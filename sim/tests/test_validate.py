"""Tests of validate.py that do not depend on which pulls are in data/.  The checks on our own tables and split are
in test_reference_data.py; validate.py on a made-up pull is in test_generic_pulls.py.
Unit (helpers, models) and integration (main on the real data folder, no sim run)."""

import contextlib
import io
import unittest

from . import helpers  # noqa: F401  (puts sim/ on sys.path)
import policies
import validate as V


class ValidateTest(unittest.TestCase):
    def test_fingerprints_cover_every_model(self):
        for n, (spec, q) in V.MODELS.items():
            if q == 'model':
                self.assertIn(n, V.FINGERPRINTS)
        self.assertEqual(V.FINGERPRINTS['Brawler v2']['int500'], 11.1)

    def test_threshold_helpers(self):
        self.assertTrue(V.within_pct(100, 125, 0.25))
        self.assertFalse(V.within_pct(100, 126, 0.25))
        self.assertFalse(V.within_pct(0, 5, 0.25))
        self.assertTrue(V.within_pct(0, 0, 0.25))
        self.assertTrue(V.fpe_ok(10, 16))
        self.assertFalse(V.fpe_ok(10, 16.1))
        self.assertTrue(V.fpe_ok(1.5, 0.2))       # both < 2
        self.assertFalse(V.fpe_ok(None, 3))

    def test_slow_rivals_padded_by_default(self):
        # pad3, adopted 2026-11-08 on the 63-match FIT set (45/63 checks, winner 30/42 vs defaults 44/63, 27/42)
        self.assertIn('pad=66,pad_bites_from=1', V.MODELS['Noob++'][0])
        self.assertIn('pad=56,pad_bites_from=2', V.MODELS['rooby'][0])
        self.assertIn('pad=12,pad_bites_from=1', V.MODELS['Aegis'][0])
        for n in ('Noob++', 'rooby', 'Aegis'):
            self.assertTrue(callable(policies.get(V.MODELS[n][0])))

    def test_median(self):
        self.assertEqual(V.median([3, None, 1, 2]), 2)
        self.assertEqual(V.median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(V.median([None]))

    def test_unknown_match_id_exits_non_zero(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err), \
                self.assertRaises(SystemExit) as cm:
            V.main(['--matches', '1,2', '--workers', '1'])   # no known id: no sim runs
        self.assertNotIn(cm.exception.code, (0, None))
        self.assertIn('1, 2', str(cm.exception.code))
        self.assertIn('not in any validation table', str(cm.exception.code))


if __name__ == '__main__':
    unittest.main()
