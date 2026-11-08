"""Tests of batch.py (unattended experiment sets).  Integration: real engine, policies and files in a temp dir."""

import contextlib
import io
import json
import os
import tempfile
import unittest

from . import helpers  # noqa: F401  (puts sim/ on sys.path)
import batch as B
import policies


class SetsTest(unittest.TestCase):
    def test_sets_resolve(self):
        self.assertIn('rivals', B.SETS)
        self.assertIn('validate', B.SETS)
        for name, st in B.SETS.items():
            for mix in st.get('mixes', []):
                self.assertTrue(1 <= len(mix) <= 4, name)
                for spec in mix:
                    self.assertTrue(callable(policies.get(spec)), spec)


class RunTest(unittest.TestCase):
    def run_set(self, argv):
        with tempfile.TemporaryDirectory() as d:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                md = B.main(argv + ['--out', d])
            lines = out.getvalue().strip().splitlines()
            self.assertEqual(lines, [md])                  # console: only the summary path
            self.assertTrue(md.startswith(d) and md.endswith('.md'))
            with open(md) as f:
                text = f.read()
            with open(md[:-3] + '.json') as f:
                data = json.load(f)
            return text, data

    def test_mix_set_writes_summary_and_json(self):
        text, data = self.run_set(['--set', 'smoke', '--seeds', '1-2', '--ticks', '40', '--size', '24',
                                   '--workers', '1'])
        self.assertLessEqual(len(text.splitlines()), 60)
        for s in ('# Experiment set smoke', 'workers 1', 'pts/gm', 'land t300', 'feeds/bite', 'freeze'):
            self.assertIn(s, text)
        self.assertEqual(len(data['matches']), 2 * len(B.SETS['smoke']['mixes']))

    def test_validate_set_on_two_matches(self):
        text, data = self.run_set(['--set', 'validate', '--ticks', '30', '--matches', '98844,99388',
                                   '--workers', '2'])
        self.assertIn('same winner', text)
        self.assertLessEqual(len(text.splitlines()), 60)
        self.assertEqual(len(data['matches']), 2)


if __name__ == '__main__':
    unittest.main()
