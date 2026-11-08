"""Fresh-clone behaviour of the data tools: a clone has no replays (they are not in the repository), so each replay
tool must stop with a one-line "run a pull first" message, never a traceback or an empty output file.  Also the
--pull / --cell / --matches arguments of the tab scripts, and LF line endings in the files the tools write.

e2e: each test copies the real script into a temporary tree with the repository layout (the scripts find the data
folder from their own location) and runs it as a subprocess with `python -I`.  Only the data is made up.
Run from the repo root:  python -m unittest discover -s tools/tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Tree(unittest.TestCase):
    """A temporary root with copies of the named scripts at their repository paths."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='chfc-')
        self.addCleanup(shutil.rmtree, self.root, True)

    def copy(self, *rel):
        for r in rel:
            dst = os.path.join(self.root, r)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(os.path.join(REPO, r), dst)

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def run_tool(self, rel, *args, pull=None):
        env = dict(os.environ)
        env.pop('CH_PULL', None)
        if pull:
            env['CH_PULL'] = pull
        env['PYTHONIOENCODING'] = 'utf-8'
        return subprocess.run([sys.executable, '-I', self.path(rel)] + list(args), cwd=self.root, env=env,
                              capture_output=True, text=True, encoding='utf-8', timeout=120)

    def assertPullFirst(self, res, *want):
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertNotIn('Traceback', res.stderr)
        self.assertIn('run a pull first', res.stderr)
        for w in want:
            self.assertIn(w, res.stderr)
        self.assertEqual(len(res.stderr.strip().splitlines()), 1, res.stderr)


class NoReplays(Tree):
    def test_valtab_missing_replays_folder(self):
        self.copy('tools/valtab.py')
        res = self.run_tool('tools/valtab.py', pull='pull9')
        self.assertPullFirst(res, 'no replays in data/pull9/replays')
        self.assertFalse(os.path.exists(self.path('data', 'pull9', 'validation-table.md')))
        self.assertFalse(os.path.exists(self.path('data', 'pull9', 'starts.json')))

    def test_valtab_empty_replays_folder_writes_nothing(self):
        self.copy('tools/valtab.py')
        os.makedirs(self.path('data', 'pull9', 'replays'))
        res = self.run_tool('tools/valtab.py', pull='pull9')
        self.assertPullFirst(res, 'no replays in data/pull9/replays')
        self.assertFalse(os.path.exists(self.path('data', 'pull9', 'validation-table.md')))
        self.assertFalse(os.path.exists(self.path('data', 'pull9', 'starts.json')))

    def test_valtab_named_replay_missing(self):
        self.copy('tools/valtab.py')
        res = self.run_tool('tools/valtab.py', '123', pull='pull9')
        self.assertPullFirst(res, 'data/pull9/replays/123.chr2.gz')

    def test_mine_missing_replays(self):
        self.copy('tools/pull2/mine.py')
        res = self.run_tool('tools/pull2/mine.py', pull='pull9')
        self.assertPullFirst(res, 'no replays in data/pull9/replays')
        self.assertFalse(os.path.exists(self.path('data', 'pull9', 'mining')))

    def test_mine_named_replay_missing(self):
        self.copy('tools/pull2/mine.py')
        os.makedirs(self.path('data', 'pull9', 'replays'))
        res = self.run_tool('tools/pull2/mine.py', '123', pull='pull9')
        self.assertPullFirst(res, 'data/pull9/replays/123.chr2.gz')

    def test_actions_replay_missing(self):
        self.copy('tools/pull2/actions.py')
        res = self.run_tool('tools/pull2/actions.py', '123')
        self.assertPullFirst(res, 'data/pull2/replays/123.chr2.gz')

    def test_actions_no_arguments_prints_usage(self):
        self.copy('tools/pull2/actions.py')
        res = self.run_tool('tools/pull2/actions.py')
        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn('Traceback', res.stderr)
        self.assertIn('usage', res.stderr.lower())

    def test_birth_order_replay_missing(self):
        self.copy('tools/pull2/birth_order.py')
        res = self.run_tool('tools/pull2/birth_order.py', '0', '123')
        self.assertPullFirst(res, 'data/pull2/')


def fake_matches(cell='Foo', n=4):
    """A match list in the site's schema (see architecture/data-pulls.md, "Doing your own pull")."""
    ms = []
    for i in range(n):
        names = [cell, 'Alpha', 'Beta', 'Gamma']
        places = ['1', '2', '3', '4'] if i % 2 == 0 else ['2', '1', '3', '4']
        cols = [dict(name=nm, player='p', place=pl, pop=str(4095 if pl == '1' else 0), peak='100', energy='0',
                     faults='0', insns='20 (30)', rating='%d → %d' % (1000 + i, 1001 + i))
                for nm, pl in zip(names, places)]
        ms.append(dict(id=200 + i, cells=names, winner=names[places.index('1')], colonies=cols))
    return dict(utc='2026-01-01T00:00:00Z', source='test', note='test', matches=ms)


class TabArgs(Tree):
    def write_matches(self, rel, data):
        p = self.path(*rel.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return p

    def check_args(self, script, *extra):
        self.copy(script)
        mf = self.write_matches('lists/mine.json', fake_matches('Foo'))
        res = self.run_tool(script, '--pull', 'pull9', '--cell', 'Foo', '--matches', mf, *extra)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('Games 4 (ids 200-203); won 2', res.stdout)
        self.assertIn('| Opponent | Foo wins / games |', res.stdout)
        raw = open(self.path('data', 'pull9', 'names.json'), 'rb').read()
        self.assertNotIn(b'\r\n', raw)                       # LF on every platform
        self.assertEqual(json.loads(raw)['200'], ['Foo', 'Alpha', 'Beta', 'Gamma'])
        return res

    def test_pull3_tab_arguments(self):
        self.check_args('tools/pull3/tab.py')

    def test_pull4_tab_arguments(self):
        res = self.check_args('tools/pull4/tab.py', '--rival', 'Alpha')
        self.assertIn('Foo vs Alpha in the same game: 4 games', res.stdout)

    def check_default(self, script, pull, matches):
        self.copy(script, 'data/%s/%s' % (pull, matches))
        res = self.run_tool(script)
        self.assertEqual(res.returncode, 0, res.stderr)
        made = open(self.path('data', pull, 'names.json'), 'rb').read()
        kept = open(os.path.join(REPO, 'data', pull, 'names.json'), 'rb').read().replace(b'\r\n', b'\n')
        self.assertEqual(made, kept)                         # defaults unchanged, LF endings
        return res.stdout

    def test_pull3_tab_defaults_unchanged(self):
        out = self.check_default('tools/pull3/tab.py', 'pull3', 'matches-scourge-2026-11-08.json')
        self.assertIn('Games 100 (ids 103128-103747); won 74 (74%)', out)

    def test_pull4_tab_defaults_unchanged(self):
        out = self.check_default('tools/pull4/tab.py', 'pull4', 'matches-contagion-2026-11-08.json')
        self.assertIn('Games 95 (ids 103614-104195); won 70', out)
        self.assertIn('Contagion vs Scourge in the same game: 13 games, Contagion placed higher in 10', out)

    def check_mining_args(self, script, pull, *args):
        """Same output from the defaults and from --pull/--cell naming the same data under another pull name."""
        self.copy(script)
        shutil.copytree(os.path.join(REPO, 'data', pull, 'mining'), self.path('data', pull, 'mining'))
        a = self.run_tool(script)
        os.rename(self.path('data', pull), self.path('data', 'pull9'))   # only --pull can find it now
        b = self.run_tool(script, '--pull', 'pull9', *args)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual(a.stdout, b.stdout)
        self.assertGreater(len(a.stdout.splitlines()), 20)

    def test_pull3_losses_arguments(self):
        self.check_mining_args('tools/pull3/losses.py', 'pull3', '--cell', 'Scourge')

    def test_pull4_games_arguments(self):
        self.check_mining_args('tools/pull4/games.py', 'pull4', '--cell', 'Contagion', '--rival', 'Scourge')

    def test_losses_without_mining_output(self):
        self.copy('tools/pull3/losses.py')
        self.assertPullFirst(self.run_tool('tools/pull3/losses.py', '--pull', 'pull9'), 'data/pull9/mining')

    def test_games_without_mining_output(self):
        self.copy('tools/pull4/games.py')
        self.assertPullFirst(self.run_tool('tools/pull4/games.py', '--pull', 'pull9'), 'data/pull9/mining')


class LineEndings(Tree):
    def test_mine_report_writes_lf(self):
        self.copy('tools/pull2/mine_report.py')
        os.makedirs(self.path('data', 'pull2', 'mining', 'races'))
        res = self.run_tool('tools/pull2/mine_report.py')
        self.assertEqual(res.returncode, 0, res.stderr)
        for f in ('refill.json', 'rest.json'):
            self.assertNotIn(b'\r\n', open(self.path('data', 'pull2', 'mining', f), 'rb').read(), f)

    def test_lists_writes_lf(self):
        self.copy('tools/pull2/lists.py')
        ms = fake_matches('Sprint')['matches']
        os.makedirs(self.path('data', 'pull2'))
        with open(self.path('data', 'pull2', 'matches-1-4.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(matches=ms), f)
        res = self.run_tool('tools/pull2/lists.py')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn(b'\r\n', open(self.path('data', 'pull2', 'winrates.json'), 'rb').read())


if __name__ == '__main__':
    unittest.main()
