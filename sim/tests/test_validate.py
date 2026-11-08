"""Tests of validate.py.  Integration: real data files (read only), real engine and policies, nothing faked."""

import contextlib
import io
import unittest

from . import helpers  # noqa: F401  (puts sim/ on sys.path)
import policies
import validate as V


class DataTest(unittest.TestCase):
    def test_table_parsed(self):
        t = V.load_table()
        self.assertEqual(len(t), 63)                             # pull 2: 36, pull 3: 15, pull 4: 12
        self.assertTrue(all(len(d['rows']) == 4 for d in t.values()))
        row = [r for r in t[98854]['rows'] if r['cell'] == 'Brawler v2'][0]
        self.assertEqual((row['t50'], row['t1000'], row['end']), (350, 3234, 4095))
        self.assertEqual(t[98854]['freeze'], 2938)
        self.assertIsNone(t[98790]['rows'][1]['E200'])          # choochoo died: None in the table
        p2 = [d['freeze'] for m, d in t.items() if V.pull_of(m) == 'pull2']
        self.assertEqual(sorted(p2)[18], 2076)                  # report: median 2076
        row = t[103128]['rows'][0]                              # pull 3, tools/valtab.py
        self.assertEqual((row['cell'], row['t50'], row['end'], row['E200']), ('AtomPush', 392, 2957, 40.184))
        self.assertEqual(t[103128]['freeze'], 927)
        self.assertEqual({V.pull_of(m) for m in t}, {'pull2', 'pull3', 'pull4'})

    def test_starts_match_table_order(self):
        t = V.load_table()
        s = V.load_starts()
        self.assertEqual(set(s), set(t))
        self.assertEqual(s[98911][3], ('AtomCrasher', (1, 1)))
        for m in t:
            self.assertEqual([n for n, _ in s[m]], [r['cell'] for r in t[m]['rows']], m)

    def test_every_cell_has_a_model_that_resolves(self):
        for d in V.load_table().values():
            for r in d['rows']:
                spec, quality = V.MODELS[r['cell']]
                self.assertIn(quality, ('exact', 'model', 'rough'))
                self.assertTrue(callable(policies.get(spec)))


class RunTest(unittest.TestCase):
    def test_short_replay_and_report(self):
        t = V.load_table()
        t = {m: t[m] for m in (98844, 99388)}
        jobs = V.make_jobs(t, V.load_starts(), dict(width=64, height=64, max_ticks=40))
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]['engine']['start_positions'], [(34, 52), (39, 10), (60, 10), (55, 14)])
        self.assertEqual(jobs[0]['names'], ['sprint', 'walker', V.MODELS['Brawler v2'][0], V.MODELS['Aegis'][0]])
        res = [V.X.play_job(j) for j in jobs]
        self.assertEqual(res[0]['starts'], {0: [34, 52], 1: [39, 10], 2: [60, 10], 3: [55, 14]})
        cmp = V.compare(t, res)
        self.assertEqual(len(cmp['matches']), 2)
        m = cmp['matches'][0]
        self.assertEqual((m['match'], m['real_winner'], m['real_freeze']), (98844, 'Sprint', 1166))
        self.assertTrue(m['clean'])
        self.assertEqual(m['sim_end'], [s['pop_at']['end'] for s in res[0]['stats']])
        self.assertGreater(sum(cmp['deltas']['idle'].values()), 0)
        self.assertEqual(len(cmp['cells']['AtomPush']['real']['t50']), 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            V.print_report(cmp)
        text = out.getvalue()
        for s in ('freeze tick', 'same winner', 'Sprint wins', 'no-event cell-ticks ending +1', 'AtomPush'):
            self.assertIn(s, text)
        self.assertIn('fingerprints', text)
        fp = cmp['cells']['AtomPush']['sim']
        for k in ('front500', 'int500', 'front1000', 'int1000', 'split_mode'):
            self.assertEqual(len(fp[k]), 1)

    def test_fingerprints_cover_every_model(self):
        for n, (spec, q) in V.MODELS.items():
            if q == 'model':
                self.assertIn(n, V.FINGERPRINTS)
        self.assertEqual(V.FINGERPRINTS['Brawler v2']['int500'], 11.1)

    def test_fit_test_split_stratified_and_fixed(self):
        t = V.load_table()
        fit, test = V.split_sets(t)
        self.assertEqual((len(fit), len(test)), (42, 21))
        self.assertFalse(set(fit) & set(test))
        self.assertEqual(sorted(fit + test), sorted(t))
        self.assertEqual(V.split_sets(t), (fit, test))          # fixed seed: same split every call
        for p, n in (('pull2', 12), ('pull3', 5), ('pull4', 4)):  # a third of each pull is TEST
            self.assertEqual(sum(V.pull_of(m) == p for m in test), n, p)
        for w in {V.cells_of(t, m)[V.winner(t[m]['rows'])] for m in t}:   # winners spread over both sets
            k = [m for m in t if V.cells_of(t, m)[V.winner(t[m]['rows'])] == w]
            if len(k) >= 3:
                self.assertTrue(set(k) & set(test) and set(k) & set(fit), w)

    def test_threshold_helpers(self):
        self.assertTrue(V.within_pct(100, 125, 0.25))
        self.assertFalse(V.within_pct(100, 126, 0.25))
        self.assertFalse(V.within_pct(0, 5, 0.25))
        self.assertTrue(V.within_pct(0, 0, 0.25))
        self.assertTrue(V.fpe_ok(10, 16))
        self.assertFalse(V.fpe_ok(10, 16.1))
        self.assertTrue(V.fpe_ok(1.5, 0.2))       # both < 2
        self.assertFalse(V.fpe_ok(None, 3))

    def test_thresholds_report_rows(self):
        t = V.load_table()
        t = {m: t[m] for m in (98844, 99388)}
        jobs = V.make_jobs(t, V.load_starts(), dict(width=64, height=64, max_ticks=30))
        cmp = V.compare(t, [V.X.play_job(j) for j in jobs])
        rows = V.thresholds(cmp)
        names = [r[0] for r in rows]
        for n in ('winner (no rough)', 'winner (all)', 'freeze median', 'frozen by t500', 'Sprint wins',
                  'fed +3 share', 'AtomPush'):
            self.assertTrue(any(x.startswith(n) for x in names), n)
        self.assertTrue(all(isinstance(r[3], bool) for r in rows))

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
