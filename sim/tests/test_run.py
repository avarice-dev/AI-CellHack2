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
                run.main(['--bots', 'idle,walker', '--start', 'corner', '--size', '10', '--ticks', '40', '--seeds', '3',
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
            run.main(['--bots', 'hunter,walker', '--start', 'corner', '--size', '8', '--ticks', '20', '--order-no-taken-jumps'])
        self.assertIn('order: no taken jumps', out.getvalue())

    def test_start_and_stun_memory_switches(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run.main(['--bots', 'rlock5,sprint', '--size', '20', '--ticks', '10', '--start', 'random',
                      '--min-dist', '6', '--metric', 'chebyshev', '--stun-memory', 'drop'])
        text = out.getvalue()
        self.assertIn('start random', text)
        self.assertIn('stun memory drop', text)
        args = run.build_parser().parse_args([])
        self.assertEqual((args.start, args.min_dist, args.metric, args.stun_memory),
                         ('random', 8, 'manhattan', 'keep'))
        kw = run.engine_kwargs(run.build_parser().parse_args(['--start', 'corner', '--inset', '2']))
        self.assertEqual((kw['start_mode'], kw['start_inset'], kw['stun_keeps_memory']), ('corner', 2, True))

    def test_feed_bonus_and_idle_gain_switches(self):
        args = run.build_parser().parse_args([])
        kw = run.engine_kwargs(args)
        self.assertEqual((kw['feed_bonus'], kw['idle_gain_prob']), (0, 0.0))
        kw = run.engine_kwargs(run.build_parser().parse_args(['--feed-bonus', '1', '--idle-gain', '0.08']))
        self.assertEqual((kw['feed_bonus'], kw['idle_gain_prob']), (1, 0.08))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run.main(['--bots', 'idle', '--size', '8', '--ticks', '5', '--idle-gain', '1', '--feed-bonus', '1'])
        self.assertIn('feed bonus 1  idle gain 1', out.getvalue())

    def test_series_rotates_slots(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run.main(['--bots', 'idle,hunter', '--start', 'corner', '--size', '8', '--ticks', '30', '--seeds', '1-2', '--verbose'])
        text = out.getvalue()
        self.assertIn('0A   idle', text)
        self.assertIn('0A   hunter', text)        # second game: hunter moved to slot 0
        self.assertIn('2 games', text)


if __name__ == '__main__':
    unittest.main()
