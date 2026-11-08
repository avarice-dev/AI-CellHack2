"""Tests of sim/cells_ref.contagion (Contagion reference policy) and of cells/gen_contagion.py.

ContagionPathTest: unit test of cells_ref.contagion; the view is faked.  Expected (action, insn, alt) values
were traced by hand from cells/gen_contagion.py's asm (every executed instruction incl. taken jumps and
ret; alt leaves taken jumps out).  The bite and gate-1 paths must equal Scourge's for every view.
ContagionSourceTest: unit test that the generated source obeys the paste rules and keeps Scourge's fast paths.
ContagionMatchTest: integration test, real engine + Contagion + real bots, nothing faked.
"""

import importlib.util
import itertools
import os
import unittest

from .helpers import E, SIM_DIR
from .test_scourge import FakeView as ScourgeView, EM, FR, EN, WA, UP, RIGHT, DOWN, LEFT, IDX, BOXED, ONLY
import cells_ref
import policies

REST = E.ACT_REST


def load_gen():
    cells = os.path.join(os.path.dirname(SIM_DIR), 'cells')
    spec = importlib.util.spec_from_file_location('gen_contagion', os.path.join(cells, 'gen_contagion.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeView(ScourgeView):
    def __init__(self, energy, x=30, y=31, w=64, h=64, ring=(), **kw):
        ScourgeView.__init__(self, energy, **kw)
        self.x, self.y, self.w, self.h = x, y, w, h
        for i in ring:                         # friends on second-ring squares
            self.cells[i] = FR


PLAIN = bytes([0, 1])


def run(mem=PLAIN, **kw):
    m = bytearray(64)
    m[:len(mem)] = mem
    return cells_ref.contagion(FakeView(**kw), m), m


def act(mem=PLAIN, **kw):
    return run(mem, **kw)[0]


ALL_RING = (1, 2, 3, 4, 5, 6, 8, 9, 10, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24)


class ContagionPathTest(unittest.TestCase):
    def test_bite_and_gate1_equal_scourge_everywhere(self):
        fars = ((), (0,), (2,), (6,), (8,), (10,), (14,), (16,), (18,), (22,), (6, 18))
        n = 0
        for types in itertools.product((EM, FR, EN, WA), repeat=4):
            kw = dict(zip(('up', 'right', 'down', 'left'), types))
            for e in (0, 4, 5, 11, 12, 15, 16, 30, 50):
                for far in fars:
                    s = cells_ref.scourge(FakeView(e, far=far, **kw), bytearray(64))
                    for mem in (PLAIN, bytes([0, 0]), bytes([0, 3, 30, 31, 1, 5])):
                        m = bytearray(64)
                        m[:len(mem)] = mem
                        before = bytes(m)
                        c = cells_ref.contagion(FakeView(e, far=far, **kw), m)
                        if s[1] <= 11:
                            self.assertEqual(c, s, (types, e, far))
                            self.assertEqual(bytes(m), before)      # no memory on the fast paths
                            n += 1
                        else:
                            self.assertGreater(c[1], 11, (types, e, far))
        self.assertGreater(n, 10000)

    def test_bite_is_5_and_refill_11(self):
        self.assertEqual(act(energy=0, up=EN), (0x30, 5, 4))
        self.assertEqual(act(energy=12, far=8, **ONLY[UP]), (0x20, 11, 10))
        self.assertEqual(act(energy=16), (0x22, 11, 10))

    def test_feed_floor_is_12(self):
        en = {UP: 8, RIGHT: 30, DOWN: 30, LEFT: 30}
        self.assertEqual(act(energy=12, en=en, far=0, **BOXED)[0], 0x40)
        self.assertEqual(cells_ref.scourge(FakeView(12, en=en, far=0, **BOXED), None)[0], REST)
        self.assertEqual(act(energy=11, en=en, far=0, **BOXED)[0], REST)
        # poorest 9 > 12 - 4: rest
        self.assertEqual(act(energy=12, en={UP: 9, RIGHT: 30, DOWN: 30, LEFT: 30}, far=0, **BOXED)[0], REST)

    def test_grab_assist(self):
        en = {UP: 3, RIGHT: 20, DOWN: 20, LEFT: 20}
        # UP has an empty neighbour (square 2): 27 + 4 + 8 = 39; taken: jz boxed only
        self.assertEqual(act(energy=8, en=en, **BOXED), (0x40, 39, 38))
        self.assertEqual(act(energy=7, en=en, **BOXED), (REST, 17, 15))           # below G
        self.assertEqual(act(energy=8, en={UP: 5, RIGHT: 20, DOWN: 20, LEFT: 20}, **BOXED)[0], REST)
        # an enemy in the 5x5: no grab assist, e < 12 -> rest
        self.assertEqual(act(energy=8, en=en, far=0, **BOXED)[0], REST)
        # target without an empty neighbour: skipped; e 8 < 12 -> rest
        # 27 + 4 + 6 (UP: no empty) + 4 x 3 (others >= 5) + cmp, jb (taken) + mov, ret
        self.assertEqual(act(energy=8, en=en, ring=ALL_RING, **BOXED), (REST, 53, 47))
        # first qualifying friend in U, R, D, L; walls (energy 0) never qualify
        self.assertEqual(act(energy=9, up=WA, right=FR, down=FR, left=FR, en={DOWN: 2, LEFT: 1})[0], 0x42)
        # a fat donor also prefers the grab target over the poorest friend
        self.assertEqual(act(energy=40, en={UP: 1, RIGHT: 4, DOWN: 20, LEFT: 20}, ring=(2, 6, 8, 10, 16, 22),
                             **BOXED)[0], 0x41)

    def test_plain_split_and_hold(self):
        self.assertEqual(act(energy=5), (0x22, 26, 26))
        self.assertEqual(act(energy=4), (REST, 17, 16))
        self.assertEqual(act(energy=15, far=0), (REST, 28, 27))
        self.assertEqual(act(energy=5, far=0, tick=2980), (0x22, 25, 23))

    def test_start_cell_far_from_edges_is_not_a_scout(self):
        (a, m) = run(mem=bytes([0, 0]), energy=10, x=30, y=31)
        self.assertEqual(a, (0x22, 46, 44))
        self.assertEqual(bytes(m[:6]), bytes([0, 1, 0, 0, 0, 0]))
        self.assertEqual(run(mem=bytes([0, 0]), energy=10, x=11, y=52)[0][0], 0x22)   # 11 from the nearest edges

    def test_start_cell_near_an_edge_sends_a_scout(self):
        cases = {(3, 31): RIGHT, (60, 31): LEFT, (30, 2): DOWN, (30, 61): UP, (10, 40): RIGHT, (2, 2): RIGHT}
        for (x, y), bear in cases.items():
            (a, m) = run(mem=bytes([0, 0]), energy=10, x=x, y=y)
            self.assertEqual(a[0], 0x20 + bear, (x, y))
            self.assertEqual(bytes(m[:6]), bytes([0, 3, x, y, bear, 10]), (x, y))
        # (3, 31): RIGHT more room than UP -> jbe .b1 not taken; DOWN 32 < 60, LEFT 3: two taken
        self.assertEqual(run(mem=bytes([0, 0]), energy=10, x=3, y=31)[0], (0x21, 62, 59))

    def test_scout_moves_along_its_bearing(self):
        (a, m) = run(mem=bytes([0, 3, 30, 31, 1, 4]), energy=5, x=31, y=31)
        self.assertEqual(a, (0x11, 40, 38))
        self.assertEqual(m[5], 3)
        self.assertEqual(m[1], 3)
        # the scout moves even with e < 16 and an empty square ahead, whatever the split order says
        self.assertEqual(act(mem=bytes([0, 3, 30, 31, 3, 4]), energy=5, x=29, y=31)[0], 0x13)

    def test_scout_stops(self):
        # the origin cell itself: clears the bit, plain split
        (a, m) = run(mem=bytes([0, 3, 30, 31, 1, 10]), energy=5, x=30, y=31)
        self.assertEqual((a, m[1]), ((0x22, 33, 30), 1))
        # out of steps
        (a, m) = run(mem=bytes([0, 3, 30, 31, 1, 0]), energy=5, x=40, y=31)
        self.assertEqual((a, m[1]), ((0x22, 35, 32), 1))
        # blocked ahead (friend on the RIGHT): plain split DOWN
        (a, m) = run(mem=bytes([0, 3, 30, 31, 1, 5]), energy=5, x=33, y=31, right=FR)
        self.assertEqual((a, m[1], m[5]), ((0x22, 39, 36), 1, 5))
        # an enemy in the 5x5: hold, and stop being a scout
        (a, m) = run(mem=bytes([0, 3, 30, 31, 1, 5]), energy=5, x=33, y=31, far=0)
        self.assertEqual((a, m[1]), ((REST, 28, 27), 1))
        # e < 5: rest, still a scout
        (a, m) = run(mem=bytes([0, 3, 30, 31, 1, 5]), energy=4, x=33, y=31)
        self.assertEqual((a, m[1]), ((REST, 17, 16), 3))

    def test_params_factory(self):
        self.assertIs(policies.get('contagion'), policies.get('contagion'))
        nos = policies.get('contagion[edge=0]')
        self.assertEqual(nos(FakeView(10, x=3, y=31), bytearray(64))[0], 0x22)


class ContagionSourceTest(unittest.TestCase):
    def test_source_rules(self):
        src = load_gen().generate()
        for bad in ('org ', 'bits ', 'section', '%include'):
            self.assertNotIn('\n' + bad, src.lower())
            self.assertNotIn('\t' + bad, src.lower())
        self.assertIn('Written with AI help', src)
        self.assertIn('Paste this whole file', src)
        self.assertLess(len(src.encode()), 64 * 1024)

    def test_fast_paths_are_scourges_verbatim(self):
        spec = importlib.util.spec_from_file_location(
            'gen_scourge', os.path.join(os.path.dirname(SIM_DIR), 'cells', 'gen_scourge.py'))
        gs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gs)

        def fast(s):
            return s[s.index('start:'):s.index('\ttest\t\tal, al')]
        self.assertEqual(fast(load_gen().generate()), fast(gs.generate()))
        self.assertNotIn('rdx', fast(load_gen().generate()))


class ContagionMatchTest(unittest.TestCase):
    def test_match_with_scout_and_no_faults(self):
        import bots
        eng = E.Engine([cells_ref.contagion, bots.hunter, bots.medic, bots.walker], width=64, height=64,
                       seed=3, max_ticks=120, start_mode='fixed',
                       start_positions={0: (3, 30), 1: (40, 10), 2: (40, 50), 3: (55, 30)})
        eng.run()
        self.assertEqual(eng.faults[0], {})
        self.assertGreaterEqual(eng.moves[0], 5)
        self.assertGreater(eng.pop[0], 50)

    def test_far_start_never_moves(self):
        import bots
        eng = E.Engine([cells_ref.contagion, bots.hunter, bots.medic, bots.walker], width=64, height=64,
                       seed=4, max_ticks=60, start_mode='fixed',
                       start_positions={0: (32, 32), 1: (5, 5), 2: (58, 5), 3: (5, 58)})
        eng.run()
        self.assertEqual(eng.faults[0], {})
        self.assertEqual(eng.moves[0], 0)


if __name__ == '__main__':
    unittest.main()
