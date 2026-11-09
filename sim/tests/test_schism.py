"""Tests of Schism (designs.md 11.1): Complacency plus feeding the growing edge.

SchismRefTest: unit test of sim/cells_ref.schism; the view is faked.  Regression anchor: on every view of the grid the
action equals policy a+f6x of sim/growth.py, the policy that was measured.
SchismGenTest: unit test of cells/gen_schism.py: the committed asm is the generator's output, tables and fast paths
are Complacency's, paste rules, legacy SSE only.
SchismMatchTest: integration test, real engine + Schism + real bots, nothing faked.
"""

import itertools
import os
import unittest

from .helpers import E
import cells_ref
import growth
import policies
from .test_vex import CELLS_DIR, ADJ, EM, FR, EN, WA, View, load

RING = (2, 6, 8, 10, 14, 16, 18, 22)
ENERGIES = (0, 5, 6, 7, 15, 16, 47, 50)


def grid():
    """Every friend / wall neighbour pattern x ring pattern x enemy spot, and all 4^4 neighbour types on an open view."""
    for types in itertools.product((FR, WA), repeat=4):
        for bits in range(256):
            for far in ((), (0,), (24,), (9,), (2,), (22,)):
                for e in ENERGIES:
                    v = View(e, types, far)
                    for k, i in enumerate(RING):
                        if i not in far:
                            v.cells[i] = EM if bits >> k & 1 else FR
                    yield v
    for types in itertools.product((EM, FR, EN, WA), repeat=4):
        for e in ENERGIES:
            yield View(e, types)


class SchismRefTest(unittest.TestCase):
    def test_action_is_policy_a_f6x(self):
        spec = growth.make_policy(**growth.POLICIES['a+f6x'][1])
        ndiff = 0
        for v in grid():
            v.x, v.y = 30, 30
            got = cells_ref.schism(v, bytearray(64))[0]
            self.assertEqual(got, spec(v, bytearray(64))[0], (v.energy, v.cells))
            ndiff += got != cells_ref.complacency(v, bytearray(64))[0]
        self.assertGreater(ndiff, 0)

    def test_registered(self):
        self.assertIs(policies.get('schism'), cells_ref.schism)

    def test_fast_paths_are_complacency(self):
        for types in ((EN, FR, FR, FR), (EM, FR, FR, FR)):
            for e in ENERGIES:
                v = View(e, types)
                self.assertEqual(cells_ref.schism(v, None), cells_ref.complacency(v, None))

    def test_rule_examples(self):
        # boxed, all friends, only DOWN's far square 22 empty: DOWN is the first candidate
        v = View(6, (FR, FR, FR, FR))
        for i in range(25):
            if i not in ADJ and i != 12:
                v.cells[i] = FR
        v.cells[22] = EM
        self.assertEqual(cells_ref.schism(v, None)[0], cells_ref.ACT_FEED + 2)


class SchismGenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check = load('check_cells')
        cls.gen = load('gen_schism')
        cls.src = cls.gen.generate()

    def test_source_matches_the_committed_asm(self):
        with open(os.path.join(CELLS_DIR, 'schism.asm'), newline='') as f:
            self.assertEqual(f.read(), self.src)

    def test_fast_path_and_tables_are_complacencys(self):
        with open(os.path.join(CELLS_DIR, 'complacency.asm'), newline='') as f:
            cp = f.read()
        def fast(src):
            return src[src.index('start:'):src.index('boxed:')]
        self.assertEqual(fast(self.src), fast(cp))
        self.assertEqual(self.src[self.src.index('bite_tbl:'):], cp[cp.index('bite_tbl:'):])

    def test_paste_rules_and_isa(self):
        src = self.src
        self.assertLess(len(src.encode()), 64 * 1024)
        ops = self.check.mnemonics(src)
        self.assertEqual(ops - self.check.ALLOWED, set())
        self.assertFalse(any(o.startswith('v') for o in ops))
        for bad in ('org ', 'bits ', 'section', '%include'):
            self.assertFalse(any(l.strip().lower().startswith(bad) for l in src.splitlines()), bad)


class SchismMatchTest(unittest.TestCase):
    def test_plays_a_match(self):
        import bots
        eng = E.Engine([cells_ref.schism, cells_ref.complacency, bots.hunter], width=64, height=64, seed=3,
                       max_ticks=150)
        eng.run()
        for c in range(2):
            self.assertEqual(eng.faults[c], {})
            self.assertGreater(eng.pop[c], 20)


if __name__ == '__main__':
    unittest.main()
