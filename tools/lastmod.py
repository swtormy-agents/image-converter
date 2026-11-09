#!/usr/bin/env python3
"""Sitemap <lastmod> from git content history (importable without running tools/gen.py)."""
import json
import os
import re
import subprocess

_GIT_ENV = {**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
_JSON_AT: dict[tuple[str, str], dict] = {}


def ensure_git_history():
    shallow = subprocess.run(
        ['git', 'rev-parse', '--is-shallow-repository'],
        capture_output=True,
        text=True,
        check=True,
        env=_GIT_ENV,
        timeout=60,
    ).stdout.strip()
    assert shallow == 'false', (
        'refusing sitemap lastmod: git clone is shallow (fetch-depth: 0 or git fetch --unshallow required)'
    )


def git_last_date(paths):
    """Latest commit date touching paths (full history, merges included)."""
    args = ['git', 'log', '-1', '--format=%cs', '--', *paths]
    r = subprocess.run(args, capture_output=True, text=True, env=_GIT_ENV, timeout=120)
    if r.returncode not in (0, 128):
        raise subprocess.CalledProcessError(r.returncode, args, r.stdout, r.stderr)
    return r.stdout.strip()


def _git_first_parent(sha):
    r = subprocess.run(
        ['git', 'rev-parse', f'{sha}^'],
        capture_output=True,
        text=True,
        env=_GIT_ENV,
        timeout=60,
    )
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _json_at_commit(sha, path):
    key = (sha, path)
    if key in _JSON_AT:
        return _JSON_AT[key]
    r = subprocess.run(
        ['git', 'show', f'{sha}:{path}'],
        capture_output=True,
        text=True,
        env=_GIT_ENV,
        timeout=60,
    )
    if r.returncode != 0:
        data = {}
    else:
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            data = {}
    _JSON_AT[key] = data
    return data


def _iter_commits(paths):
    r = subprocess.run(
        ['git', 'log', '--format=%H %cs', '--', *paths],
        capture_output=True,
        text=True,
        check=True,
        env=_GIT_ENV,
        timeout=120,
    )
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, date = line.split(' ', 1)
        yield sha, date


def build_json_slug_dates(path, langs):
    """Newest commit date per (lang, slug) where that subtree changed vs first parent (or first appear)."""
    dates = {}
    for sha, commit_date in _iter_commits([path]):
        parent = _git_first_parent(sha)
        cur = _json_at_commit(sha, path)
        if parent is None:
            for lang in langs:
                block = cur.get(lang) or {}
                if not isinstance(block, dict):
                    continue
                for slug in block:
                    if slug.startswith('_'):
                        continue
                    dates.setdefault((lang, slug), commit_date)
            continue
        prev = _json_at_commit(parent, path)
        for lang in langs:
            cur_block = cur.get(lang) if isinstance(cur.get(lang), dict) else {}
            prev_block = prev.get(lang) if isinstance(prev.get(lang), dict) else {}
            slugs = set(cur_block) | set(prev_block)
            for slug in slugs:
                if slug.startswith('_'):
                    continue
                if (lang, slug) in dates:
                    continue
                if cur_block.get(slug) != prev_block.get(slug):
                    dates[(lang, slug)] = commit_date
    return dates


def clear_json_cache():
    _JSON_AT.clear()


def lastmod(lang, page, langs, doc_pages):
    """Max date: tools/i18n/{lang}.json plus per-slug seo.json / faq.json content edits."""
    dates = []
    d = git_last_date([f'tools/i18n/{lang}.json'])
    if d:
        dates.append(d)
    if page == 'index.html' or page in doc_pages:
        pass
    elif page.endswith('.html'):
        slug = page.replace('.html', '')
        for table in (_SEO_SLUG_DATES, _FAQ_SLUG_DATES):
            hit = table.get((lang, slug))
            if hit:
                dates.append(hit)
    assert dates, f'no git date for {lang}/{page}'
    out = max(dates)
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', out), f'bad git date for {lang}/{page}: {out!r}'
    return out


def init_slug_date_tables(langs):
    global _SEO_SLUG_DATES, _FAQ_SLUG_DATES
    clear_json_cache()
    _SEO_SLUG_DATES = build_json_slug_dates('tools/i18n/seo.json', langs)
    clear_json_cache()
    _FAQ_SLUG_DATES = build_json_slug_dates('tools/i18n/faq.json', langs)
    clear_json_cache()


_SEO_SLUG_DATES: dict = {}
_FAQ_SLUG_DATES: dict = {}
