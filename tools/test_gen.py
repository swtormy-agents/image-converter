#!/usr/bin/env python3
"""Generator guards: placeholder markers must never ship in rendered HTML."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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


if __name__ == '__main__':
    unittest.main()
