"""Integration test of run.py: real engine, real bots, real files in a temp dir; nothing faked."""

import contextlib
import io
import os
import tempfile
import unittest

from . import helpers  # noqa: F401  (puts sim/ on sys.path)
import run


class RunnerTest(unittest.TestCase):
    def test_single_match_writes_csv_and_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            csv = os.path.join(d, 'm.csv')
            snap = os.path.join(d, 'm.txt')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                run.main(['--bots', 'idle,walker', '--size', '10', '--ticks', '40', '--seeds', '3',
                          '--csv', csv, '--snap', snap, '--snap-every', '20'])
            with open(csv) as f:
                rows = f.read().splitlines()
            self.assertEqual(rows[0].split(',')[0], 'tick')
            last_tick = int(rows[-1].split(',')[0])
            self.assertEqual(len(rows), 1 + last_tick + 1)      # header + ticks 0..N
            self.assertEqual(rows[1], '0,1,1,0,0,10,10,0,0')
            with open(snap) as f:
                text = f.read()
            self.assertTrue(text.startswith('tick 0 '))
            self.assertIn('pl  slot bot', out.getvalue())

    def test_order_no_taken_jumps_switch(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run.main(['--bots', 'hunter,walker', '--size', '8', '--ticks', '20', '--order-no-taken-jumps'])
        self.assertIn('order: no taken jumps', out.getvalue())

    def test_series_rotates_slots(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run.main(['--bots', 'idle,hunter', '--size', '8', '--ticks', '30', '--seeds', '1-2', '--verbose'])
        text = out.getvalue()
        self.assertIn('0A   idle', text)
        self.assertIn('0A   hunter', text)        # second game: hunter moved to slot 0
        self.assertIn('2 games', text)


if __name__ == '__main__':
    unittest.main()
