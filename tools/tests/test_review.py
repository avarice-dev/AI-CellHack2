"""tools/replay/review.py on a three-tick replay small enough to count by hand.

e2e: the real script runs as a subprocess (`python -I`) in a temporary tree with the repository layout; only the
replay and names.json are made up.  The expected numbers are counted by hand from the definitions in review.py's
docstring, not taken from its output.
Run from the repo root:  python -m unittest discover -s tools/tests
"""
import csv
import gzip
import json
import os
import struct
import unittest

from test_replay_tools import Tree

EAT, FEED, BIRTH, MOVE, DEATH = 4, 5, 1, 2, 3


def cell(cid, colony, x, y, e):
    return struct.pack('<IBHHB', cid, colony, x, y, e)


def event(kind, *args):
    if kind in (EAT, FEED):
        return bytes([kind]) + struct.pack('<II', *args) + bytes(1)
    if kind == BIRTH:
        return bytes([kind]) + cell(*args)
    if kind == MOVE:
        return bytes([kind]) + struct.pack('<IHH', *args)
    return bytes([kind]) + struct.pack('<I', *args)


def tick(t, events, energies):
    return (bytes([1]) + struct.pack('<I', t) + bytes(8) + struct.pack('<I', len(events)) + b''.join(events)
            + struct.pack('<I', len(energies)) + bytes(energies))


def replay():
    """8x8 board, 2 colonies.
    Start: cell 0 (colony 0) at (1,1) energy 10; cell 1 (colony 1) at (2,1) energy 3, touching cell 0;
    cell 2 (colony 1) at (6,6) energy 6, alone.
    Tick 0: cell 0 eats cell 1 before cell 1 acts; cell 1 dies, its square (2,1) is freed beside colony 0.
            Cell 2 does nothing with 6 energy and empty neighbours (hold).
    Tick 1: cell 3 (colony 0) is born on (2,1) (colony 0 takes the freed enemy square; cell 0 is its parent).
            Cell 2 holds again and ends the tick at 50 energy.
    Tick 2: cell 3 feeds cell 0; cell 0 (7 energy, empty neighbours) does nothing (hold); cell 2 at 50 does
            nothing (capidle)."""
    hdr = b'CHR2' + struct.pack('<HHHHBHQI', 4, 64, 8, 8, 2, 0, 0, 3) + bytes(16)
    key = bytes([2]) + struct.pack('<II', 0, 3) + cell(0, 0, 1, 1, 10) + cell(1, 1, 2, 1, 3) + cell(2, 1, 6, 6, 6)
    t0 = tick(0, [event(EAT, 0, 1), event(DEATH, 1)], [12, 6])
    t1 = tick(1, [event(BIRTH, 3, 0, 2, 1, 3)], [7, 50, 3])
    t2 = tick(2, [event(FEED, 3, 0)], [8, 50, 2])
    return hdr + key + t0 + t1 + t2


class ReviewByHand(Tree):
    def setUp(self):
        super().setUp()
        os.makedirs(self.path('data', 'zz', 'replays'))
        with gzip.open(self.path('data', 'zz', 'replays', '7.chr2.gz'), 'wb') as f:
            f.write(replay())
        with open(self.path('data', 'zz', 'names.json'), 'w', encoding='utf-8') as f:
            json.dump({'7': ['Foo v2', 'Bar']}, f)

    def rows(self):
        res = self.run_tool('review', '--pull', 'zz', '--csv=' + self.path('out.csv'))
        self.assertEqual(res.returncode, 0, res.stderr)
        with open(self.path('out.csv'), encoding='utf-8') as f:
            return res.stdout, {r['name']: r for r in csv.DictReader(f)}

    def test_start_and_cells(self):
        out, rows = self.rows()
        foo, bar = rows['Foo v2'], rows['Bar']
        self.assertEqual((foo['x'], foo['y'], foo['wall'], foo['near']), ('1', '1', '1', '1'))
        self.assertEqual((bar['x'], bar['y'], bar['wall'], bar['near']), ('2', '1', '1', '1'))
        self.assertEqual((foo['final'], bar['final'], foo['place'], bar['place']), ('2', '1', '1', '2'))
        self.assertEqual(foo['ticks'], '3')
        self.assertIn('Foo v2', out)
        self.assertIn('wrote', out)

    def test_actions_per_cell_tick(self):
        _, rows = self.rows()
        foo, bar = rows['Foo v2'], rows['Bar']
        # Foo: 4 cell-ticks (1 + 1 + 2): 1 birth, 1 feed, 1 hold, 1 contact
        self.assertEqual([float(foo['t0_' + k]) for k in ('split', 'move', 'feed', 'hold', 'capidle', 'contact')],
                         [25.0, 0.0, 25.0, 25.0, 0.0, 25.0])
        # Bar: 4 cell-ticks (2 + 1 + 1): 2 holds, 1 capidle, 1 contact
        self.assertEqual([float(bar['t0_' + k]) for k in ('split', 'move', 'feed', 'hold', 'capidle', 'contact')],
                         [0.0, 0.0, 0.0, 50.0, 25.0, 25.0])

    def test_bite_order_deaths_and_freed_squares(self):
        _, rows = self.rows()
        foo, bar = rows['Foo v2'], rows['Bar']
        self.assertEqual((float(foo['t0_bitfirst']), float(bar['t0_bitfirst'])), (0.0, 100.0))
        self.assertEqual((foo['t0_deaths'], bar['t0_deaths']), ('0', '1'))
        self.assertEqual((foo['t0_enemyfreed'], float(foo['t0_take'])), ('1', 100.0))
        self.assertEqual((bar['t0_enemyfreed'], float(bar['t0_take'])), ('0', 0.0))


if __name__ == '__main__':
    unittest.main()
