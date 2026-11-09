#!/usr/bin/env python3
"""Generator guards: placeholder markers must never ship in rendered HTML."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import lastmod

# Keep in sync with tools/gen.py PLACEHOLDER_RE.
PLACEHOLDER_RE = re.compile(
    r'(?:lorem\s+ipsum|'
    r'\b(?:placeholder|lorem|tbd|fixme|xxx)\b|'
    r'TODO:\s*\S|'
    r'\[\[(?:fill|placeholder|tbd|xxx|lorem)[^\]]*\]\]|'
    r'\{\{(?:fill|placeholder|tbd|lorem)[^}]*\}\})',
    re.I,
)


def assert_no_placeholders(text, where):
    m = PLACEHOLDER_RE.search(text or '')
    assert not m, f'placeholder marker in {where}: {m.group(0)!r}'


class PlaceholderGuard(unittest.TestCase):
    def test_rejects_known_markers(self):
        for bad in (
            'lorem ipsum dolor',
            'PLACEHOLDER TEXT HERE',
            'TODO: fill in',
            '[[placeholder]]',
            '{{fill later}}',
            'Content TBD for launch',
        ):
            with self.subTest(sample=bad):
                with self.assertRaises(AssertionError):
                    assert_no_placeholders(bad, 'test')

    def test_allows_real_copy(self):
        assert_no_placeholders('Convert PNG images to WebP in your browser.', 'test')


class GenBuild(unittest.TestCase):
    def test_gen_runs_clean(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / 'tools' / 'gen.py')],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        self.assertIn('sitemap URLs', r.stdout)


class JsonSlugLastmod(unittest.TestCase):
    def test_content_edit_under_existing_key_moves_lastmod(self):
        langs = ['en', 'ru']
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env = {
                **os.environ,
                'GIT_AUTHOR_NAME': 'test',
                'GIT_AUTHOR_EMAIL': 'test@example.com',
                'GIT_COMMITTER_NAME': 'test',
                'GIT_COMMITTER_EMAIL': 'test@example.com',
            }
            i18n = td / 'tools' / 'i18n'
            i18n.mkdir(parents=True)
            faq_v1 = {
                'en': {
                    'avif-to-jpg': [{'q': 'Q1', 'a': 'Answer one'}],
                    'heic-to-jpg': [{'q': 'H1', 'a': 'Heic answer'}],
                },
                'ru': {'heic-to-jpg': [{'q': 'R1', 'a': 'Ru heic'}]},
            }
            (i18n / 'faq.json').write_text(json.dumps(faq_v1), encoding='utf-8')
            subprocess.run(['git', 'init'], cwd=td, check=True, capture_output=True, env=env)
            subprocess.run(['git', 'add', 'tools/i18n/faq.json'], cwd=td, check=True, capture_output=True, env=env)
            subprocess.run(
                ['git', 'commit', '-m', 'seed faq'],
                cwd=td,
                check=True,
                capture_output=True,
                env={**env, 'GIT_AUTHOR_DATE': '2026-01-01T00:00:00+0000', 'GIT_COMMITTER_DATE': '2026-01-01T00:00:00+0000'},
            )
            faq_v2 = json.loads((i18n / 'faq.json').read_text(encoding='utf-8'))
            faq_v2['en']['avif-to-jpg'][0]['a'] = 'Answer two'
            (i18n / 'faq.json').write_text(json.dumps(faq_v2), encoding='utf-8')
            subprocess.run(['git', 'add', 'tools/i18n/faq.json'], cwd=td, check=True, capture_output=True, env=env)
            subprocess.run(
                ['git', 'commit', '-m', 'tweak avif answer only'],
                cwd=td,
                check=True,
                capture_output=True,
                env={**env, 'GIT_AUTHOR_DATE': '2026-01-15T00:00:00+0000', 'GIT_COMMITTER_DATE': '2026-01-15T00:00:00+0000'},
            )
            cwd = os.getcwd()
            try:
                os.chdir(td)
                lastmod.clear_json_cache()
                dates = lastmod.build_json_slug_dates('tools/i18n/faq.json', langs)
                self.assertEqual(dates[('en', 'avif-to-jpg')], '2026-01-15')
                self.assertEqual(dates[('en', 'heic-to-jpg')], '2026-01-01')
                self.assertEqual(dates[('ru', 'heic-to-jpg')], '2026-01-01')
                self.assertNotIn(('ru', 'avif-to-jpg'), dates)
            finally:
                os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
