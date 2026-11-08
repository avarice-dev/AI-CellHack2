"""The simulator tools on a pull that is not ours: pulls are found in the data folder, not listed in the code.

Integration: real validate.py / treadmill.py / batch.py, real engine and policies; the data folder is a temporary
directory with a made-up pull (validate.DATA points at it).  Nothing of ours is mocked.
"""

import contextlib
import csv
import gzip
import io
import json
import os
import shutil
import tempfile
import unittest

from . import helpers  # noqa: F401  (puts sim/ on sys.path)
import batch as B
import treadmill as T
import validate as V

CELLS = ('Hunter', 'Walker', 'Medic', 'Zed')          # 'Zed' has no sim model
STARTS = ((10, 10), (50, 10), (10, 50), (50, 50))


def table_text(ids, cells=CELLS):
    out = ['| match | colony | pop t50 | t100 | t200 | t500 | t1000 | end | E t200 | E t1000 | feeds/eat | freeze |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for m in ids:
        for c, n in enumerate(cells):
            out.append('| %d | %s | %d | 20 | 30 | 40 | 50 | 60 | 10.0 | 12.0 | - | 900 |' % (m, n, 10 + c))
    return '\n'.join(out) + '\n'


def make_pull(root, pull, ids, cells=CELLS):
    d = os.path.join(root, pull)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'validation-table.md'), 'w', encoding='utf-8') as f:
        f.write(table_text(ids, cells))
    with open(os.path.join(d, 'starts.json'), 'w', encoding='utf-8') as f:
        json.dump({str(m): [[n, x, y] for n, (x, y) in zip(cells, STARTS)] for m in ids}, f)


class TempData(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='chgp-')
        self.addCleanup(shutil.rmtree, self.root, True)
        old = V.DATA
        V.DATA = self.root
        V._IDS.clear()
        self.addCleanup(setattr, V, 'DATA', old)
        self.addCleanup(V._IDS.clear)


class Discover(TempData):
    def test_new_pull_found_without_code_edit(self):
        make_pull(self.root, 'zz', (1, 2))
        self.assertEqual(V.pulls(), ['zz'])
        self.assertEqual(sorted(V.load_table()), [1, 2])
        self.assertEqual(V.pull_of(2), 'zz')

    def test_natural_order_and_folders_without_table_ignored(self):
        make_pull(self.root, 'pull10', (10,))
        make_pull(self.root, 'pull2', (2,))
        os.makedirs(os.path.join(self.root, 'splits'))
        self.assertEqual(V.pulls(), ['pull2', 'pull10'])

    def test_pull_filter(self):
        make_pull(self.root, 'aa', (1,))
        make_pull(self.root, 'bb', (2,))
        self.assertEqual(sorted(V.load_table(pulls=['bb'])), [2])

    def test_starts_json_of_every_pull_read(self):
        make_pull(self.root, 'aa', (1,))
        make_pull(self.root, 'bb', (2,))
        s = V.load_starts()
        self.assertEqual(sorted(s), [1, 2])
        self.assertEqual(s[1][3], ('Zed', (50, 50)))


class UnknownCell(TempData):
    def test_unknown_cell_falls_back_rough_with_warning(self):
        make_pull(self.root, 'zz', (1,))
        V._WARNED.discard('Zed')
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            jobs = V.make_jobs(V.load_table(), V.load_starts(), dict(width=64, height=64, max_ticks=10))
        self.assertEqual(jobs[0]['names'][3], 'hunter')
        self.assertIn('Zed', err.getvalue())
        self.assertEqual(V.model_of('Zed'), ('hunter', 'rough'))

    def test_models_option_takes_json_or_file(self):
        V.apply_models('{"Zed": "walker"}')
        self.addCleanup(V.MODELS.pop, 'Zed', None)
        self.assertEqual(V.model_of('Zed'), ('walker', 'model'))
        p = os.path.join(self.root, 'models.json')
        with open(p, 'w') as f:
            json.dump({'Zed': 'medic'}, f)
        V.apply_models(p)
        self.assertEqual(V.model_of('Zed'), ('medic', 'model'))


class MainOnTempPull(TempData):
    def test_validate_main_split_file_and_run(self):
        make_pull(self.root, 'zz', (1, 2, 3))
        split = os.path.join(self.root, 'my-split.json')
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            V.main(['--split', split, '--extend-split'])
        sets = V.load_split(split)
        self.assertEqual(sorted(sets), [1, 2, 3])
        with open(split, encoding='utf-8') as f:
            before = f.read()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            V.main(['--split', split, '--extend-split'])          # nothing new: no id moves
        with open(split, encoding='utf-8') as f:
            self.assertEqual(f.read(), before)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            V.main(['--split', split, '--pull', 'zz', '--matches', '1', '--workers', '1', '--ticks', '20',
                    '--models', '{"Zed": "walker"}'])
        V.MODELS.pop('Zed', None)
        self.assertIn('1 games', out.getvalue())

    def test_validate_matches_unknown_names_found_pulls(self):
        make_pull(self.root, 'zz', (1,))
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(io.StringIO()):
            V.main(['--matches', '7'])
        self.assertIn('zz', str(cm.exception.code))

    def test_batch_validate_unknown_match_exits(self):
        make_pull(self.root, 'zz', (1,))
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
            B.main(['--set', 'validate', '--matches', '7', '--ticks', '10', '--out', os.path.join(self.root, 'o')])
        self.assertNotIn(cm.exception.code, (0, None))

    def test_treadmill_unknown_match_exits(self):
        make_pull(self.root, 'zz', (1,))
        V.extend_split(V.load_table(), os.path.join(self.root, 'splits', 'split.json'))
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
            T.main(['--set', 'all', '--matches', '7', '--ticks', '10'])
        self.assertNotIn(cm.exception.code, (0, None))


class TreadmillReal(TempData):
    def test_load_real_uses_discovered_pulls(self):
        make_pull(self.root, 'zz', (5,))
        mining = os.path.join(self.root, 'zz', 'mining')
        os.makedirs(os.path.join(mining, 'races'))
        with gzip.open(os.path.join(mining, 'races', '5.csv.gz'), 'wt', newline='') as f:
            w = csv.writer(f)
            w.writerow(['tDeath', 'deadCol', 'killerCol', 'contMask', 'fillCol', 'dt', 'fillKind', 'fillE'])
            w.writerow([100, 0, 1, 3, 1, 2, 1, 5])
        with open(os.path.join(mining, '5.json'), 'w') as f:
            json.dump({'pop': [[1, 1, 1, 1]] * 600}, f)
        r = T.load_real(5)
        self.assertIsNotNone(r)
        self.assertEqual(len(r), 4)
        self.assertEqual(r[0]['pend'], 1)

    def test_land_cells_fall_back_to_most_common_modelled(self):
        def m(p500, pend):
            return {'p500': p500, 'pend': pend}
        V.MODELS['Qx'] = ('walker', 'model')
        self.addCleanup(V.MODELS.pop, 'Qx', None)
        real = [('Qx', None, m(100, 50))]
        sim = [('Qx', None, m(100, 60))]
        self.assertEqual(T.land_cells(real), ['Qx'])
        self.assertEqual(T.land_check(real, sim, T.land_cells(real))[0][0], 'Qx')


if __name__ == '__main__':
    unittest.main()
