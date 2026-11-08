"""Integration tests of experiments.py: real engine, real policies, real worker processes; nothing faked."""

import contextlib
import io
import json
import os
import tempfile
import unittest

from . import helpers  # noqa: F401  (puts sim/ on sys.path)
import experiments as X

SMALL = dict(width=24, height=24, max_ticks=120, start_mode='random', start_min_dist=8)


def strip_secs(results):
    return [{k: v for k, v in r.items() if k != 'secs'} for r in results]


class JobsTest(unittest.TestCase):
    def test_slots_rotate_per_game(self):
        jobs = X.make_jobs([['a', 'b', 'c', 'd']], [1, 2, 3, 4, 5], {})
        self.assertEqual([j['names'] for j in jobs],
                         [['a', 'b', 'c', 'd'], ['b', 'c', 'd', 'a'], ['c', 'd', 'a', 'b'],
                          ['d', 'a', 'b', 'c'], ['a', 'b', 'c', 'd']])
        self.assertEqual([j['seed'] for j in jobs], [1, 2, 3, 4, 5])

    def test_no_rotate(self):
        jobs = X.make_jobs([['a', 'b'], ['c', 'd']], [1, 2], {}, rotate=False)
        self.assertEqual([(j['mix'], j['names']) for j in jobs],
                         [(0, ['a', 'b']), (0, ['a', 'b']), (1, ['c', 'd']), (1, ['c', 'd'])])


class PlayJobTest(unittest.TestCase):
    def test_stats_agree_with_engine_totals(self):
        job = X.make_jobs([['rlock5', 'walker', 'sprint', 'rfatgrab']], [3], SMALL, stats=True)[0]
        r = X.play_job(job)
        self.assertEqual(sorted(x['points'] for x in r['ranking']), [0, 1, 2, 3])
        for x in r['ranking']:
            s = r['stats'][x['colony']]
            self.assertEqual(s['name'], job['names'][x['colony']])
            self.assertEqual(s['splits'], x['births'])
            self.assertEqual(s['deaths'], x['deaths'])
            self.assertEqual(s['pop_at']['end'], x['pop'])
            self.assertEqual(set(s['pop_at']), {50, 100, 200, 300, 500, 1000, 2000, 3000, 'end'})
            self.assertEqual(set(s['energy_at']), {200, 500, 1000})
            self.assertEqual(s['pop_at'][1000], x['pop'])      # match shorter than 1000: end state
        m = r['bite_first']
        self.assertEqual(len(m), 4)
        self.assertEqual(sum(m[a][a] for a in range(4)), 0)
        self.assertGreater(sum(map(sum, m)), 0)
        self.assertGreater(sum(s['eats_enemy'] for s in r['stats']), 0)

    def test_front_energy_counts_cells_with_an_adjacent_enemy(self):
        e = helpers.board([helpers.script({})] * 2, w=6, h=3)
        e.add_cell(0, 0, 0, 10)     # interior of colony 0 (no enemy adjacent)
        e.add_cell(1, 1, 0, 30)     # front: enemy at (2,1)
        e.add_cell(2, 0, 0, 20)     # front: enemy at (2,1) below it
        e.add_cell(2, 1, 1, 7)      # front of colony 1
        e.add_cell(5, 2, 1, 9)      # isolated
        self.assertEqual(X.front_energy(e), [(25.0, 2), (7.0, 1), (None, 0), (None, 0)])

    def test_feeds_per_eat_and_front_in_stats(self):
        job = X.make_jobs([['rpump', 'ratompush']], [2], dict(SMALL, max_ticks=150), stats=True)[0]
        r = X.play_job(job)
        for s in r['stats']:
            self.assertEqual(set(s['front_at']), {200, 500, 1000})
            self.assertEqual(set(s['interior_at']), {200, 500, 1000})
            self.assertIn('feeds_per_bite', s)
            self.assertEqual(sum(s['split_energy'].values()), s['splits'])
            self.assertTrue(all(k >= 2 for k in s['split_energy']))
            mean, count = s['front_at'][1000]
            self.assertTrue(mean is None or 0 < mean <= 50)

    def test_no_stats_by_default(self):
        job = X.make_jobs([['idle', 'walker']], [1], SMALL)[0]
        r = X.play_job(job)
        self.assertNotIn('stats', r)
        self.assertNotIn('bite_first', r)


class FreezeTickTest(unittest.TestCase):
    """freeze_tick: the replay analyzer's definition (tools/pull2/analyze.js): the earliest t such that
    every colony's population at every later tick stays within 5% of its population at t."""

    def test_definition(self):
        self.assertEqual(X.freeze_tick([[10, 10, 10]]), 0)
        self.assertEqual(X.freeze_tick([[1, 50, 100, 100, 104]]), 2)
        self.assertEqual(X.freeze_tick([[100, 100, 100, 94]]), 3)       # the last tick always qualifies
        self.assertEqual(X.freeze_tick([[100, 100, 100, 100], [5, 40, 0, 0]]), 2)   # 0 stays 0
        self.assertEqual(X.freeze_tick([[100, 96, 104, 100]]), 2)       # at 96 the later max 104 > 100.8

    def test_in_match_stats(self):
        job = X.make_jobs([['rpump', 'ratompush']], [2], dict(SMALL, max_ticks=150), stats=True)[0]
        r = X.play_job(job)
        self.assertTrue(0 <= r['freeze_tick'] <= r['ticks'])
        self.assertEqual(len(r['pop_history']), 2)
        self.assertEqual(len(r['pop_history'][0]), r['ticks'] + 1)
        self.assertEqual(r['pop_history'][0][0], 1)
        self.assertEqual(r['freeze_tick'], X.freeze_tick(r['pop_history']))
        for c, s in enumerate(r['stats']):
            self.assertEqual(s['pop_at'][3000], r['pop_history'][c][-1])
            e = s['eats_enemy']
            self.assertEqual(s['feeds_per_bite'], s['feeds'] / e if e else None)

    def test_feeds_per_bite_and_freeze_in_summary(self):
        jobs = X.make_jobs([['rpump', 'ratompush']], [1, 2], dict(SMALL, max_ticks=150), stats=True)
        res = X.run_jobs(jobs, workers=1)
        d = X.summarize_stats(res)[0]
        self.assertEqual(sorted(d['freeze_ticks']), sorted(r['freeze_tick'] for r in res))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            X.print_summary([['rpump', 'ratompush']], res)
        text = out.getvalue()
        for label in ('land t300', 'land t2000', 'land t3000', 'feeds per bite', 'interior energy t500',
                      'freeze tick'):
            self.assertIn(label, text)


class WorkerLimitTest(unittest.TestCase):
    """CPU limit (user, 2026-11-08): at most 4 worker processes (never 6, the machine's total), 4 by
    default, low priority.  Was 2 until 2026-11-08."""

    def test_default_and_cap(self):
        self.assertEqual(X.DEFAULT_WORKERS, 4)
        self.assertEqual(X.MAX_WORKERS, 4)
        self.assertEqual(X.worker_count(None), 4)
        self.assertEqual(X.worker_count(6), 4)
        self.assertEqual(X.worker_count(5), 4)
        self.assertEqual(X.worker_count(3), 3)
        self.assertEqual(X.worker_count(1), 1)
        self.assertEqual(X.worker_count(0), 1)

    def test_cli_default(self):
        args = X.build_parser().parse_args(['--mix', 'idle'])
        self.assertEqual(X.worker_count(args.workers), 4)

    def test_lower_priority_is_safe_to_call(self):
        X.lower_priority()
        X.lower_priority()


class ParallelTest(unittest.TestCase):
    def test_parallel_matches_serial(self):
        jobs = X.make_jobs([['rlock5', 'hunter', 'walker'], ['idle', 'rblind3']], [1, 2], SMALL, stats=True)
        a = X.run_jobs(jobs, workers=1)
        b = X.run_jobs(jobs, workers=2)
        self.assertEqual(strip_secs(a), strip_secs(b))
        self.assertEqual([r['seed'] for r in a], [1, 2, 1, 2])

    def test_summary_per_mix_and_policy(self):
        jobs = X.make_jobs([['idle', 'walker']], [1, 2, 3, 4], dict(SMALL, max_ticks=40))
        res = X.run_jobs(jobs, workers=2)
        summ = X.summarize(res)
        self.assertEqual(set(summ[0]), {'idle', 'walker'})
        for name, a in summ[0].items():
            self.assertEqual(a['games'], 4)
        self.assertEqual(sum(a['wins'] for a in summ[0].values()), 4)
        self.assertEqual(sum(a['points'] for a in summ[0].values()), 4 * (3 + 2))


class CliTest(unittest.TestCase):
    def test_cli_detail_and_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'r.json')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                X.main(['--mix', 'rlock5,walker,sprint,rfatgrab', '--seeds', '1-2', '--size', '24',
                        '--ticks', '80', '--min-dist', '8', '--workers', '2', '--detail', '--json', path])
            text = out.getvalue()
            self.assertIn('mix 1: rlock5,walker,sprint,rfatgrab', text)
            self.assertIn('pts/gm', text)
            self.assertIn('bites first', text)
            self.assertIn('pop t50', text)
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(len(data['matches']), 2)


if __name__ == '__main__':
    unittest.main()
