"""Our own reference data: the committed tables, starts, mining output and FIT/TEST split of data pulls 2-5.

These tests check our data and the results built from it (135 matches; split.json: FIT 90 / TEST 45).  They read
only the pulls named in REF, so a pull of your own in data/ does not change them.  The tools themselves are tested
on made-up pulls in a temporary folder (test_generic_pulls.py, tools/tests/test_fresh_clone.py).
Integration: real data files (read only), real engine and policies, nothing faked.
"""

import contextlib
import io
import unittest

from . import helpers  # noqa: F401  (puts sim/ on sys.path)
import policies
import treadmill as T
import validate as V

REF = ('pull2', 'pull3', 'pull4', 'pull5')


class OurTables(unittest.TestCase):
    def test_table_parsed(self):
        t = V.load_table(pulls=REF)
        self.assertEqual(len(t), 135)                            # pull 2: 36, pull 3: 15, pull 4: 12, pull 5: 72
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
        self.assertEqual({V.pull_of(m) for m in t}, {'pull2', 'pull3', 'pull4', 'pull5'})
        row = t[106357]['rows'][1]                              # pull 5
        self.assertEqual((row['cell'], row['end']), ('Contagion', 4095))

    def test_starts_match_table_order(self):
        t = V.load_table(pulls=REF)
        s = V.load_starts(REF)
        self.assertEqual(set(s), set(t))
        self.assertEqual(s[98911][3], ('AtomCrasher', (1, 1)))
        for m in t:
            self.assertEqual([n for n, _ in s[m]], [r['cell'] for r in t[m]['rows']], m)

    def test_every_cell_has_a_model_that_resolves(self):
        for d in V.load_table(pulls=REF).values():
            for r in d['rows']:
                spec, quality = V.MODELS[r['cell']]
                self.assertIn(quality, ('exact', 'model', 'rough'))
                self.assertTrue(callable(policies.get(spec)))


    def test_pull2_starts_json_equals_report_section_5(self):
        # data/pull2/starts.json was written once (2026-11-08) from section 5 of the pull 2 report, which validate.py
        # parsed before; the two must agree.
        import os, re
        with open(os.path.join(V.ROOT, 'data', 'ladder-data-2-2026-11-08.md'), encoding='utf-8') as f:
            txt = f.read()
        sec = txt.split('## 5.')[1].split('```')[1]
        rep = {}
        for line in sec.strip().splitlines():
            m, rest = line.split(':', 1)
            rep[int(m)] = [(n.strip(), (int(x), int(y))) for n, x, y in re.findall(r'([^;]+?) \((\d+),(\d+)\)', rest)]
        self.assertEqual(V.load_starts(['pull2']), rep)


class OurSplit(unittest.TestCase):
    def test_fit_test_split_stratified_and_fixed(self):
        t = V.load_table(pulls=REF)
        fit, test = V.split_sets(t)
        self.assertEqual((len(fit), len(test)), (90, 45))
        self.assertFalse(set(fit) & set(test))
        self.assertEqual(sorted(fit + test), sorted(t))
        self.assertEqual(V.split_sets(t), (fit, test))          # fixed file: same split every call
        for p, n in (('pull2', 12), ('pull3', 5), ('pull4', 4), ('pull5', 24)):  # a third of each pull is TEST
            self.assertEqual(sum(V.pull_of(m) == p for m in test), n, p)
        for w in {V.cells_of(t, m)[V.winner(t[m]['rows'])] for m in t}:   # winners spread over both sets
            k = [m for m in t if V.cells_of(t, m)[V.winner(t[m]['rows'])] == w]
            if len(k) >= 3:
                self.assertTrue(set(k) & set(test) and set(k) & set(fit), w)

    def test_old_matches_keep_their_set(self):
        # The sim was tuned on the FIT set of pulls 2-4 (63 matches, FIT 42 / TEST 21): adding pull 5 must not
        # move any of them.  Pulls 2-4 keep the rule applied to their own 63 ids; pull 5 is split on its own.
        t = V.load_table(pulls=REF)
        sets = V.load_split()
        old = [m for m in t if V.pull_of(m) in ('pull2', 'pull3', 'pull4')]
        fit, test = V.stratified_split(t, old)
        self.assertEqual((len(fit), len(test)), (42, 21))
        self.assertEqual({m: sets[m] for m in old}, dict([(m, 'FIT') for m in fit] + [(m, 'TEST') for m in test]))
        new = [m for m in t if V.pull_of(m) == 'pull5']
        fit, test = V.stratified_split(t, new)
        self.assertEqual({m: sets[m] for m in new}, dict([(m, 'FIT') for m in fit] + [(m, 'TEST') for m in test]))

    def test_extend_split_keeps_existing_sets(self):
        import json, os, tempfile
        t = V.load_table(pulls=REF)
        sets = V.load_split()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'split.json')
            flipped = {m: ('TEST' if v == 'FIT' else 'FIT') for m, v in sets.items() if V.pull_of(m) != 'pull5'}
            with open(path, 'w') as f:
                json.dump({'sets': {str(m): v for m, v in flipped.items()}}, f)
            with self.assertRaises(ValueError):                 # pull 5 has no set yet
                V.split_sets(t, path)
            V.extend_split(t, path)
            got = V.load_split(path)
            self.assertEqual({m: got[m] for m in flipped}, flipped)   # existing entries untouched
            self.assertEqual({m: got[m] for m in t if V.pull_of(m) == 'pull5'},
                             {m: sets[m] for m in t if V.pull_of(m) == 'pull5'})


class OurMatchesReplayed(unittest.TestCase):
    def test_short_replay_and_report(self):
        t = V.load_table(pulls=REF)
        t = {m: t[m] for m in (98844, 99388)}
        jobs = V.make_jobs(t, V.load_starts(REF), dict(width=64, height=64, max_ticks=40))
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

    def test_thresholds_report_rows(self):
        t = V.load_table(pulls=REF)
        t = {m: t[m] for m in (98844, 99388)}
        jobs = V.make_jobs(t, V.load_starts(REF), dict(width=64, height=64, max_ticks=30))
        cmp = V.compare(t, [V.X.play_job(j) for j in jobs])
        rows = V.thresholds(cmp)
        names = [r[0] for r in rows]
        for n in ('winner (no rough)', 'winner (all)', 'freeze median', 'frozen by t500', 'Sprint wins',
                  'fed +3 share', 'AtomPush'):
            self.assertTrue(any(x.startswith(n) for x in names), n)
        self.assertTrue(all(isinstance(r[3], bool) for r in rows))


class OurMining(unittest.TestCase):
    def test_missing_races_file_gives_none(self):
        # 98797's raw replay was deleted in pull 2 (size cap), so it has no races file
        self.assertIsNone(T.load_real(98797))

    def test_later_pulls_load(self):
        # pull 3 (103128) and pull 4 (103756): races from data/<pull>/mining, populations from the mining pop
        for m in (103128, 103756):
            r = T.load_real(m)
            self.assertIsNotNone(r, m)
            self.assertEqual(len(r), 4)
        self.assertEqual(T.load_real(103128)[0]['pend'], 2957)


if __name__ == '__main__':
    unittest.main()
