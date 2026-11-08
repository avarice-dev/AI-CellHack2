"""Tests of Complacency (designs.md section 9): Scourge plus early free splitting.

ComplacencyRefTest: unit test of sim/cells_ref.make_complacency; the view is faked.  On every view of the grid it
must return Scourge's action, except on Scourge's prey-hold path (rest, 27 instructions) before tick T, where it
splits into the first freed, else first empty, neighbour of DOWN, RIGHT, UP, LEFT; instruction counts are Scourge's
except on the 5 <= e < 16 middle path (traced by hand from cells/gen_complacency.py's asm).
ComplacencyGenTest: unit test of cells/gen_complacency.py: the committed asm is the generator's output, the bite and
gate-1 source lines are Scourge's verbatim, tables are Scourge's, paste rules, legacy SSE only (no VEX: calib-s).
ComplacencyMatchTest: integration test, real engine + Complacency + real bots, nothing faked.
"""

import os
import unittest

from .helpers import E
import cells_ref
import policies
from .test_vex import CELLS_DIR, ADJ, EM, FR, EN, WA, View, load
import itertools

FARS = ((), (0,), (2,), (22,), (6,), (8,), (10,), (14,), (16,), (18,), (6, 18), (24,))
TICKS = (0, 199, 200, 299, 300, 2979, 2980)
ORDER = (17, 13, 7, 11)                  # DOWN RIGHT UP LEFT
DIRS = {7: 0, 13: 1, 17: 2, 11: 3}
FREED_BY = {7: (6, 8), 13: (8, 14, 18), 17: (16, 18), 11: (6, 10, 16)}


def grid():
    for types in itertools.product((EM, FR, EN, WA), repeat=4):
        for e in (0, 4, 5, 8, 11, 12, 15, 16, 47, 50):
            for far in FARS:
                for tick in TICKS:
                    yield View(e, types, far, tick)


def expected(v, T):
    """(action, insn) from Scourge's result and the bet, written from the spec, not from the policy."""
    a, n, _ = cells_ref.scourge(v, None)
    c = v.cells
    middle = (not any(c[i] == EN for i in ADJ) and any(c[i] == EM for i in ADJ) and 5 <= v.energy
              and n in (24, 25, 27))     # Scourge's 5x5-check paths
    if not middle:
        return a, n
    empty = [i for i in ORDER if c[i] == EM]
    freed = [i for i in empty if any(c[k] == EN for k in FREED_BY[i])]
    split = 0x20 + DIRS[(freed or empty)[0]]
    if T >= 2980:
        return split, 16
    if v.tick < T:
        return split, 17
    return a, n + 2


class ComplacencyRefTest(unittest.TestCase):
    def test_scourge_except_the_bet(self):
        for T in (200, 300, 3000):
            pol = cells_ref.make_complacency(free_until=T)
            nbet = 0
            for v in grid():
                got = pol(v, None)[:2]
                want = expected(v, T)
                self.assertEqual(got, want, (T, v.energy, v.cells, v.tick))
                if got[0] != cells_ref.scourge(v, None)[0]:
                    nbet += 1
                    self.assertEqual(cells_ref.scourge(v, None)[1], 27)
                    self.assertTrue(v.tick < T)
            self.assertGreater(nbet, 0, T)

    def test_default_is_the_committed_cell(self):
        gen = load('gen_complacency')
        self.assertIs(policies.get('complacency'), cells_ref.complacency)
        v = View(8, (EM, FR, FR, FR), far=(0,), tick=2000)     # enemy far in view, middle energy
        self.assertEqual(cells_ref.complacency(v, None)[0],
                         cells_ref.make_complacency(free_until=gen.FREE_UNTIL)(v, None)[0])

    def test_diag_probe(self):
        pol = cells_ref.make_complacency(diag_hold=True)
        self.assertEqual(pol(View(8, (EM, FR, FR, FR), far=(0,)), None), (0x20, 18, 18))     # far enemy: split
        self.assertEqual(pol(View(8, (EM, FR, FR, FR), far=(16,)), None), (0x01, 21, 20))    # diagonal: hold
        self.assertEqual(pol(View(8, (EM, FR, FR, FR), far=(16,), tick=2980), None), (0x20, 19, 17))


class ComplacencyGenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check = load('check_cells')
        cls.gen = load('gen_complacency')
        cls.src = cls.gen.generate()

    def test_source_matches_the_committed_asm(self):
        with open(os.path.join(CELLS_DIR, 'complacency.asm'), newline='') as f:
            self.assertEqual(f.read(), self.src)

    def test_bite_and_gate1_are_scourges(self):
        def fast(src):
            return src[src.index('start:'):src.index('\ttest\t\tal, al')]
        with open(os.path.join(CELLS_DIR, 'scourge.asm'), newline='') as f:
            self.assertEqual(fast(self.src), fast(f.read()))

    def test_tables_are_scourges(self):
        with open(os.path.join(CELLS_DIR, 'scourge.asm'), newline='') as f:
            sc = f.read()
        self.assertEqual(self.src[self.src.index('bite_tbl:'):], sc[sc.index('bite_tbl:'):])

    def test_paste_rules_and_isa(self):
        src = self.src
        self.assertLess(len(src.encode()), 64 * 1024)
        self.assertIn('Scourge plus early free splitting', src.splitlines()[0])
        ops = self.check.mnemonics(src)
        self.assertEqual(ops - self.check.ALLOWED, set())
        self.assertFalse(any(o.startswith('v') for o in ops))          # no VEX (calib-s)
        self.assertEqual(self.check.vex_dst_not_src1(src), [])
        for bad in ('org ', 'bits ', 'section', '%include'):
            self.assertFalse(any(l.strip().lower().startswith(bad) for l in src.splitlines()), bad)

    def test_variants_generate(self):
        for T in (200, 300, 500):
            s = self.gen.generate(T)
            self.assertIn('cmp\t\tdword [rdi + VIEW_TICK], %d' % T, s)
            self.assertIn('kTwoLo:', s)
        s = self.gen.generate(3000)
        self.assertNotIn('kTwoLo:', s)
        self.assertNotIn('VIEW_TICK', s.split('\nstart:\n')[1].split('boxed:')[0])


class ComplacencyMatchTest(unittest.TestCase):
    def test_plays_a_match(self):
        import bots
        eng = E.Engine([cells_ref.complacency, cells_ref.scourge, bots.hunter], width=64, height=64, seed=3,
                       max_ticks=150)
        eng.run()
        for c in range(2):
            self.assertEqual(eng.faults[c], {})
            self.assertGreater(eng.pop[c], 20)


if __name__ == '__main__':
    unittest.main()
