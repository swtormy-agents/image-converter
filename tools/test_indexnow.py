#!/usr/bin/env python3
"""Unit tests for tools/indexnow.py. Run: python3 tools/test_indexnow.py"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import indexnow  # noqa: E402

HOST = "noclaudkit.com"
BASE = f"https://{HOST}/image-converter/"
BASE_RU = f"https://{HOST}/image-converter/ru/"
BASE_ZH = f"https://{HOST}/image-converter/zh/"
HOME_URLS = [BASE, BASE_RU, BASE_ZH]

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
<url><loc>https://noclaudkit.com/image-converter/</loc>
<xhtml:link rel="alternate" hreflang="en" href="https://noclaudkit.com/image-converter/"/>
<xhtml:link rel="alternate" hreflang="ru" href="https://noclaudkit.com/image-converter/ru/"/>
<xhtml:link rel="alternate" hreflang="zh-Hans" href="https://noclaudkit.com/image-converter/zh/"/>
</url>
<url><loc>https://noclaudkit.com/image-converter/ru/</loc>
<xhtml:link rel="alternate" hreflang="en" href="https://noclaudkit.com/image-converter/"/>
<xhtml:link rel="alternate" hreflang="ru" href="https://noclaudkit.com/image-converter/ru/"/>
<xhtml:link rel="alternate" hreflang="zh-Hans" href="https://noclaudkit.com/image-converter/zh/"/>
</url>
<url><loc>https://noclaudkit.com/image-converter/zh/</loc>
<xhtml:link rel="alternate" hreflang="en" href="https://noclaudkit.com/image-converter/"/>
<xhtml:link rel="alternate" hreflang="ru" href="https://noclaudkit.com/image-converter/ru/"/>
<xhtml:link rel="alternate" hreflang="zh-Hans" href="https://noclaudkit.com/image-converter/zh/"/>
</url>
</urlset>
"""

DIRTY_URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>http://noclaudkit.com/image-converter/</loc></url>
<url><loc>https://example.com/phish</loc></url>
<url><loc>https://noclaudkit.com/image-converter/ok.html</loc></url>
<url><loc>https://noclaudkit.com/ok/</loc></url>
</urlset>
"""

INDEPENDENT_URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://noclaudkit.com/image-converter/a/</loc></url>
<url><loc>https://noclaudkit.com/image-converter/b/</loc></url>
</urlset>
"""


def write_repo(tmp: Path, urlset: str = URLSET) -> Path:
    tmp.joinpath("sitemap.xml").write_text(urlset, encoding="utf-8")
    return tmp


def mapped(tmp: Path, files: list[str]) -> list[str]:
    locs, alts = indexnow.parse_local_urlsets(tmp)
    return indexnow.map_changed_files(files, locs, alts)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def make_multicommit_repo(tmp: Path) -> dict[str, str]:
    write_repo(tmp, urlset=INDEPENDENT_URLSET)
    run_git(tmp, "init", "-b", "main")
    run_git(tmp, "config", "user.name", "Test")
    run_git(tmp, "config", "user.email", "test@example.com")
    run_git(tmp, "add", ".")
    run_git(tmp, "commit", "-m", "base")
    c1 = run_git(tmp, "rev-parse", "HEAD")
    tmp.joinpath("a").mkdir()
    tmp.joinpath("a", "index.html").write_text("a\n", encoding="utf-8")
    run_git(tmp, "add", "a/index.html")
    run_git(tmp, "commit", "-m", "add a")
    c2 = run_git(tmp, "rev-parse", "HEAD")
    tmp.joinpath("b").mkdir()
    tmp.joinpath("b", "index.html").write_text("b\n", encoding="utf-8")
    run_git(tmp, "add", "b/index.html")
    run_git(tmp, "commit", "-m", "add b")
    c3 = run_git(tmp, "rev-parse", "HEAD")
    return {"c1": c1, "c2": c2, "c3": c3}


class CanonicalUrlTests(unittest.TestCase):
    def test_accepts_image_converter_paths(self):
        self.assertTrue(indexnow.is_canonical_url(BASE))
        self.assertTrue(indexnow.is_canonical_url(BASE_RU))
        self.assertTrue(
            indexnow.is_canonical_url("https://noclaudkit.com/image-converter/heic-to-jpg.html")
        )

    def test_rejects_root_and_other_hosts(self):
        self.assertFalse(indexnow.is_canonical_url("https://noclaudkit.com/"))
        self.assertFalse(indexnow.is_canonical_url("http://noclaudkit.com/image-converter/"))
        self.assertFalse(indexnow.is_canonical_url("https://example.com/image-converter/"))
        self.assertFalse(indexnow.is_canonical_url("https://noclaudkit.com/image-converter/x?y=1"))


class MappingTests(unittest.TestCase):
    def test_home_html_expands_to_all_language_homes(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            self.assertEqual(mapped(tmp, ["index.html"]), HOME_URLS)
            self.assertEqual(mapped(tmp, ["ru/index.html"]), HOME_URLS)

    def test_shared_assets_map_to_all_sitemap_urls(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            for path in ("theme.js", "tools/gen.py", "build/app.css"):
                self.assertEqual(mapped(tmp, [path]), HOME_URLS, path)

    def test_non_page_files_ignored(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            ignored = ["robots.txt", "llms.txt", "tools/indexnow.py"]
            self.assertEqual(mapped(tmp, ignored), [])

    def test_landing_page_maps_to_html_loc(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            urlset = URLSET.replace(
                "</urlset>",
                "<url><loc>https://noclaudkit.com/image-converter/heic-to-jpg.html</loc></url>\n</urlset>",
            )
            write_repo(tmp, urlset=urlset)
            loc = "https://noclaudkit.com/image-converter/heic-to-jpg.html"
            self.assertEqual(mapped(tmp, ["heic-to-jpg.html"]), [loc])


class KeyTests(unittest.TestCase):
    def test_uses_root_site_key(self):
        with tempfile.TemporaryDirectory() as raw:
            key, location = indexnow.read_key(Path(raw))
            self.assertEqual(key, indexnow.INDEXNOW_KEY)
            self.assertEqual(location, indexnow.KEY_LOCATION)
            self.assertEqual(location, f"https://{HOST}/{indexnow.INDEXNOW_KEY}.txt")


class AllLocsTests(unittest.TestCase):
    def test_all_flag_returns_every_loc(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            urls = indexnow.collect_urls(tmp, None, None, None, all_mode=True)
            self.assertEqual(urls, HOME_URLS)

    def test_cli_all_env(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            stdout = io.StringIO()
            with mock.patch.dict(os.environ, {"INDEXNOW_ALL": "true"}, clear=False):
                with mock.patch.object(sys, "stdout", stdout):
                    code = indexnow.main(["--dry-run", "--repo-root", str(tmp)])
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["urlList"], HOME_URLS)


class ShaValidationTests(unittest.TestCase):
    def test_full_sha_regex(self):
        good = "a" * 40
        self.assertTrue(indexnow.is_full_sha(good))
        self.assertFalse(indexnow.is_full_sha("a" * 39))
        self.assertFalse(indexnow.is_full_sha("a" * 41))
        self.assertFalse(indexnow.is_full_sha("g" * 40))
        self.assertFalse(indexnow.is_full_sha("A" * 40))
        self.assertFalse(indexnow.is_full_sha("deadbeef;rm -rf /" + "0" * 28))

    def test_explicit_before_rejects_bad_sha(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            for bad in (shas["c1"][:39], shas["c1"] + "0", "not-a-sha", "G" * 40):
                with self.assertRaises(indexnow.IndexNowError) as ctx:
                    indexnow.validate_explicit_before(tmp, bad)
                self.assertIn("40-character hex", str(ctx.exception))


class RangeTests(unittest.TestCase):
    def test_changed_files_map_to_locs(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            self.assertEqual(
                indexnow.collect_urls(tmp, None, shas["c1"], shas["c3"]),
                [
                    "https://noclaudkit.com/image-converter/a/",
                    "https://noclaudkit.com/image-converter/b/",
                ],
            )

    def test_sitemap_only_change_includes_loc(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            new_sitemap = INDEPENDENT_URLSET.replace(
                "<lastmod>", ""
            ).replace(
                "image-converter/b/",
                "image-converter/b/",
            )
            new_sitemap = INDEPENDENT_URLSET.replace(
                "</url>",
                "<lastmod>2026-10-27</lastmod></url>",
                1,
            )
            tmp.joinpath("sitemap.xml").write_text(new_sitemap, encoding="utf-8")
            run_git(tmp, "add", "sitemap.xml")
            run_git(tmp, "commit", "-m", "touch sitemap")
            c4 = run_git(tmp, "rev-parse", "HEAD")
            urls = indexnow.collect_urls(tmp, None, shas["c3"], c4)
            self.assertIn("https://noclaudkit.com/image-converter/a/", urls)


class WorkflowFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT.parent / ".github/workflows/indexnow.yml"
        cls.text = cls.path.read_text(encoding="utf-8")

    def test_dispatch_inputs_and_security(self):
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("INDEXNOW_BEFORE: ${{ inputs.after }}", self.text)
        self.assertIn("INDEXNOW_ALL: ${{ inputs.all }}", self.text)
        self.assertIn("persist-credentials: false", self.text)
        self.assertIn("contents: read", self.text)
        self.assertIn(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            self.text,
        )
        run_lines = [line for line in self.text.splitlines() if line.lstrip().startswith("run:")]
        self.assertEqual(run_lines, ["        run: python3 tools/indexnow.py --submit"])
        for line in run_lines:
            self.assertNotIn("${{", line)


class LiveRepoTests(unittest.TestCase):
    def test_real_sitemap_locs_are_canonical(self):
        repo = ROOT.parent
        locs, _ = indexnow.parse_local_urlsets(repo)
        self.assertGreater(len(locs), 10)
        self.assertTrue(all(indexnow.is_canonical_url(url) for url in locs))


if __name__ == "__main__":
    unittest.main()
