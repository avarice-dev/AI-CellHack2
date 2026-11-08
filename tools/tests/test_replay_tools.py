"""The replay tools (tools/replay/) on a pull of your own: no pull, cell, rival or match list of ours is assumed.

e2e: each test copies tools/replay/ into a temporary tree with the repository layout and runs the real scripts as
subprocesses with `python -I`.  Only the data is made up (a match list, mine.py output, names.json).
Run from the repo root:  python -m unittest discover -s tools/tests
"""
import csv
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = ('tab', 'mine', 'valtab', 'actions', 'losses', 'games', 'mine_report', 'birth_order')


def fake_matches(cell='Foo', n=4, start=200):
    ms = []
    for i in range(n):
        names = [cell, 'Alpha', 'Beta', 'Gamma']
        places = ['1', '2', '3', '4'] if i % 2 == 0 else ['2', '1', '3', '4']
        cols = [dict(name=nm, player='p', place=pl, pop=str(4095 if pl == '1' else 0), peak='100', energy='0',
                     faults='0', insns='20 (30)', rating='%d → %d' % (1000 + i, 1001 + i))
                for nm, pl in zip(names, places)]
        ms.append(dict(id=start + i, cells=names, winner=names[places.index('1')], colonies=cols))
    return dict(utc='2026-01-01T00:00:00Z', source='test', note='test', matches=ms)


class Tree(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='chrt-')
        self.addCleanup(shutil.rmtree, self.root, True)
        shutil.copytree(os.path.join(REPO, 'tools', 'replay'), self.path('tools', 'replay'),
                        ignore=shutil.ignore_patterns('__pycache__'))

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def run_tool(self, name, *args):
        env = dict(os.environ)
        env.pop('CH_PULL', None)
        env['PYTHONIOENCODING'] = 'utf-8'
        return subprocess.run([sys.executable, '-I', self.path('tools', 'replay', name + '.py')] + list(args),
                              cwd=self.root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=120)

    def mining(self, pull, games):
        """mine.py output for games [(id, names, placement)]: pop per tick, end, a small races file."""
        out = self.path('data', pull, 'mining')
        os.makedirs(os.path.join(out, 'races'), exist_ok=True)
        for rid, names, placement in games:
            pop = [[t + 1 + 10 * (4 - placement[c]) for c in range(4)] for t in range(1200)]
            with open(os.path.join(out, '%d.json' % rid), 'w', encoding='utf-8') as f:
                json.dump(dict(id=rid, names=names, pop=pop, end=dict(placement=placement, pop=pop[-1]), ticks=1200,
                               rest={str(c): {'0': {'10': [5, 90, 5]}} for c in range(4)}, touched=[10] * 12,
                               early={'0,b,2': 3}, validation=dict(kfChecked=1, kfMismatch=0, countMismatch=0,
                                                                   gridConflicts=0)), f)
            with gzip.open(os.path.join(out, 'races', '%d.csv.gz' % rid), 'wt', newline='') as f:
                w = csv.writer(f)
                w.writerow(['tDeath', 'deadCol', 'killerCol', 'contMask', 'fillCol', 'dt', 'fillKind', 'fillE'])
                w.writerow([100, 0, 1, 3, 1, 2, 1, 5])
                w.writerow([600, 1, 0, 3, 0, 3, 1, 4])


class NoDefaultPull(Tree):
    def test_every_tool_needs_pull_and_names_the_pulls_found(self):
        for p in ('aa', 'bb'):
            os.makedirs(self.path('data', p))
        for t in TOOLS:
            args = ('0', '1') if t == 'birth_order' else ('1',) if t == 'actions' else ()
            res = self.run_tool(t, *args)
            self.assertNotEqual(res.returncode, 0, t)
            self.assertNotIn('Traceback', res.stderr, t)
            self.assertIn('--pull', res.stderr, t)
            self.assertIn('aa, bb', res.stderr, t)


class TabOwnList(Tree):
    def test_without_matches_reads_the_pulls_own_list(self):
        os.makedirs(self.path('data', 'zz'))
        with open(self.path('data', 'zz', 'matches-foo-2026-01-01.json'), 'w', encoding='utf-8') as f:
            json.dump(fake_matches('Foo'), f)
        res = self.run_tool('tab', '--pull', 'zz', '--cell', 'Foo')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('Games 4 (ids 200-203)', res.stdout)
        self.assertIn('200', json.load(open(self.path('data', 'zz', 'names.json'), encoding='utf-8')))

    def test_without_matches_and_no_list_stops(self):
        os.makedirs(self.path('data', 'zz'))
        res = self.run_tool('tab', '--pull', 'zz', '--cell', 'Foo')
        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn('Traceback', res.stderr)
        self.assertIn('data/zz', res.stderr.replace('\\', '/'))
        self.assertNotIn('pull3', res.stderr)
        self.assertFalse(os.path.exists(self.path('data', 'zz', 'names.json')))

    def test_rival_optional_and_parts(self):
        os.makedirs(self.path('data', 'zz'))
        with open(self.path('data', 'zz', 'matches-a.json'), 'w', encoding='utf-8') as f:
            json.dump(fake_matches('Foo', 6), f)
        res = self.run_tool('tab', '--pull', 'zz', '--cell', 'Foo', '--parts', '2')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('older 3: won', res.stdout)
        self.assertNotIn('in the same game', res.stdout)
        res = self.run_tool('tab', '--pull', 'zz', '--cell', 'Foo', '--rival', 'Alpha')
        self.assertIn('oldest third (200-201)', res.stdout)
        self.assertIn('Foo vs Alpha in the same game: 6 games', res.stdout)


class MiningTables(Tree):
    GAMES = [(1, ['Foo', 'Bar', 'Baz', 'Qux'], [2, 1, 3, 4]),
             (2, ['Bar', 'Foo', 'Baz', 'Qux'], [1, 2, 3, 4]),
             (3, ['Foo', 'Baz', 'Qux', 'Zip'], [1, 2, 3, 4]),
             (4, ['Nop', 'Baz', 'Qux', 'Zip'], [1, 2, 3, 4])]          # a game without Foo

    def test_losses_skips_games_without_cell_and_names_it(self):
        self.mining('zz', self.GAMES)
        res = self.run_tool('losses', '--pull', 'zz', '--cell', 'Foo')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('1 game(s) without Foo left out', res.stderr)
        self.assertNotIn('Scourge', res.stdout)
        self.assertIn('Fights between Foo (S)', res.stdout)
        self.assertIn('every colony in the 4 replays', res.stdout)

    def test_games_skips_games_without_cell_and_names_cells(self):
        self.mining('zz', self.GAMES)
        res = self.run_tool('games', '--pull', 'zz', '--cell', 'Foo', '--rival', 'Bar')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('1 game(s) without Foo left out', res.stderr)
        self.assertNotIn('Contagion', res.stdout)
        self.assertNotIn('Scourge', res.stdout)
        self.assertIn('### Foo wins (1)', res.stdout)
        self.assertIn('- Bar (these games): n=2', res.stdout)

    def test_games_rival_optional(self):
        self.mining('zz', self.GAMES)
        res = self.run_tool('games', '--pull', 'zz', '--cell', 'Foo')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn('Scourge', res.stdout)

    def test_mine_report_named_pull_cell_and_rivals(self):
        self.mining('zz', self.GAMES)
        res = self.run_tool('mine_report', '--pull', 'zz', '--cell', 'Foo', '--rivals', 'Bar')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('### (a4) Foo vs Bar', res.stdout)
        self.assertIn('| Foo won % |', res.stdout)
        for f in ('refill.json', 'rest.json'):
            self.assertNotIn(b'\r\n', open(self.path('data', 'zz', 'mining', f), 'rb').read(), f)
        res = self.run_tool('mine_report', '--pull', 'zz')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn('(a4)', res.stdout)


class BirthOrderNames(Tree):
    def test_names_from_names_json_keep_every_word(self):
        os.makedirs(self.path('data', 'zz', 'replays'))
        with open(self.path('data', 'zz', 'names.json'), 'w', encoding='utf-8') as f:
            json.dump({'7': ['Brawler v2', 'Foo', 'Bar', 'Baz']}, f)
        # a replay with a header and one tick record in which colonies 0 and 1 are born, 0 first
        import struct
        hdr = b'CHR2' + struct.pack('<HHHHBHQI', 4, 64, 64, 4, 0, 0, 0, 0) + bytes(16)
        ev = bytes([1]) + bytes(4) + bytes([0]) + bytes(5)            # birth, colony 0
        ev1 = bytes([1]) + bytes(4) + bytes([1]) + bytes(5)           # birth, colony 1
        tick = bytes([1]) + struct.pack('<I', 5) + bytes(8) + struct.pack('<I', 2 * 300) + (ev + ev1) * 300 \
            + struct.pack('<I', 0)
        with gzip.open(self.path('data', 'zz', 'replays', '7.chr2.gz'), 'wb') as f:
            f.write(hdr + tick)
        res = self.run_tool('birth_order', '--pull', 'zz', '0', '7')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('Brawler v2   before Foo', res.stdout)


if __name__ == '__main__':
    unittest.main()
