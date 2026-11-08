"""Tests of sim/cells_ref.scourge (Scourge reference policy) and of cells/gen_scourge.py's tables.

ScourgePathTest: unit test of cells_ref.scourge; the view is faked.  Expected (action, insn, alt) values
were traced by hand from cells/gen_scourge.py's asm (every executed instruction incl. taken jumps and
ret; alt leaves taken jumps out).
ScourgeTableTest: unit test that the generator's act/thr tables agree with the reference for every
combination of the 10 squares the refill window reads, and that the source obeys the paste rules.
ScourgeMatchTest: integration test, real engine + Scourge + real bots, nothing faked.
"""

import importlib.util
import itertools
import os
import unittest

from .helpers import E, SIM_DIR
import cells_ref
import policies

EM, FR, EN, WA = E.CELL_EMPTY, E.CELL_FRIEND, E.CELL_ENEMY, E.CELL_WALL
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
IDX = {UP: 7, RIGHT: 13, DOWN: 17, LEFT: 11}
REST = E.ACT_REST


def load_gen():
    path = os.path.join(os.path.dirname(SIM_DIR), 'cells', 'gen_scourge.py')
    spec = importlib.util.spec_from_file_location('gen_scourge', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeView(object):
    def __init__(self, energy, tick=0, up=EM, right=EM, down=EM, left=EM, far=(), en=None):
        self.energy = energy
        self.tick = tick
        self.cells = [EM] * 25
        self.cells[12] = FR
        self.energies = [0] * 25
        self.energies[12] = energy
        for d, t in ((UP, up), (RIGHT, right), (DOWN, down), (LEFT, left)):
            self.cells[IDX[d]] = t
            if t in (FR, EN):
                self.energies[IDX[d]] = 20
        for d, v in (en or {}).items():
            self.energies[IDX[d]] = v
        for i in ((far,) if isinstance(far, int) else far):
            self.cells[i] = EN
            self.energies[i] = 9


def run(**kw):
    return cells_ref.scourge(FakeView(**kw), bytearray(64))


BOXED = dict(up=FR, right=FR, down=FR, left=FR)
ONLY = {UP: dict(right=FR, down=FR, left=FR), RIGHT: dict(up=FR, down=FR, left=FR),
        DOWN: dict(up=FR, right=FR, left=FR), LEFT: dict(up=FR, right=FR, down=FR)}


class ScourgePathTest(unittest.TestCase):
    def test_bite_is_5_in_every_direction(self):
        self.assertEqual(run(energy=0, up=EN), (0x30, 5, 4))
        self.assertEqual(run(energy=50, right=EN), (0x31, 5, 4))
        self.assertEqual(run(energy=3, down=EN), (0x32, 5, 4))
        self.assertEqual(run(energy=3, left=EN, far=8), (0x33, 5, 4))

    def test_multi_bite_choices_are_sprints(self):
        for types in itertools.product((EM, FR, EN, WA), repeat=4):
            if EN not in types:
                continue
            kw = dict(zip(('up', 'right', 'down', 'left'), types))
            self.assertEqual(run(energy=30, **kw)[:2], (cells_ref.sprint(FakeView(30, **kw), None)[0], 5))

    def test_refill_is_11_for_every_covered_square(self):
        covered = {UP: (6, 8), RIGHT: (8, 14, 18), DOWN: (16, 18), LEFT: (6, 10, 16)}
        for d, squares in covered.items():
            for sq in squares:
                self.assertEqual(run(energy=12, far=sq, **ONLY[d]), (0x20 + d, 11, 10), (d, sq))

    def test_refill_needs_child_6(self):
        # e = 11: no refill; enemy in view, e < 16 -> hold: rest at 27 (taken: jnz threat)
        self.assertEqual(run(energy=11, far=8, **ONLY[UP]), (REST, 27, 26))
        self.assertEqual(run(energy=12, far=8, **ONLY[UP])[0], 0x20)

    def test_refill_prefers_freed_square_in_split_order(self):
        # enemy at 18 frees RIGHT and DOWN; DOWN first (D, R, U, L); UP is empty but not freed
        self.assertEqual(run(energy=12, far=18, left=FR), (0x22, 11, 10))
        # enemy at 6 frees UP and LEFT; DOWN and RIGHT are empty but not freed -> UP
        self.assertEqual(run(energy=12, far=6), (0x20, 11, 10))
        # same at e >= 16: still the freed square, not the plain split order
        self.assertEqual(run(energy=40, far=6), (0x20, 11, 10))

    def test_beyond_up_and_down_are_not_read(self):
        # squares 2 and 22 lie outside the refill window: no refill at 12 ...
        self.assertEqual(run(energy=12, far=2, **ONLY[UP]), (REST, 27, 26))
        self.assertEqual(run(energy=12, far=22, **ONLY[DOWN]), (REST, 27, 26))
        # ... but a normal split at 16 (prey rule: child >= 8), at the same 11
        self.assertEqual(run(energy=16, far=2, **ONLY[UP]), (0x20, 11, 10))

    def test_plain_split(self):
        self.assertEqual(run(energy=16), (0x22, 11, 10))           # e >= 16: gate 1
        self.assertEqual(run(energy=5), (0x22, 24, 24))            # 5 <= e < 16, no enemy in view
        self.assertEqual(run(energy=15, down=FR), (0x21, 24, 24))
        self.assertEqual(run(energy=5, down=WA, right=WA), (0x20, 24, 24))

    def test_prey_rule(self):
        # an enemy anywhere in the 5x5 (corner 0, 24, or a square the refill window does not read)
        for sq in (0, 24, 2, 9, 15, 20):
            self.assertEqual(run(energy=15, far=sq), (REST, 27, 26), sq)
            self.assertEqual(run(energy=16, far=sq), (0x22, 11, 10), sq)

    def test_late_split_from_2980(self):
        self.assertEqual(run(energy=5, far=0, tick=2980), (0x22, 25, 23))
        self.assertEqual(run(energy=5, far=0, tick=2979), (REST, 27, 26))
        self.assertEqual(run(energy=6, far=8, tick=2999, **ONLY[UP]), (0x20, 25, 23))

    def test_rest_low_energy(self):
        self.assertEqual(run(energy=4), (REST, 17, 16))
        self.assertEqual(run(energy=0, far=0, tick=2999), (REST, 17, 16))
        self.assertEqual(run(energy=4, **BOXED), (REST, 17, 15))
        self.assertEqual(run(energy=15, **BOXED), (REST, 17, 15))   # below the donor floor 16

    def test_feed_poorest_friend(self):
        # boxed 47, four friends at 20: 21 + 7 + 5 * 3 + cmp, ja + ret; taken: jz, jae x3
        self.assertEqual(run(energy=47, **BOXED), (0x40, 46, 42))
        self.assertEqual(run(energy=50, en={LEFT: 5, DOWN: 9}, **BOXED)[0], 0x43)
        self.assertEqual(run(energy=50, en={RIGHT: 5, LEFT: 5}, **BOXED)[0], 0x41)

    def test_donor_floor_and_margin(self):
        self.assertEqual(run(energy=16, en={UP: 12, RIGHT: 30, DOWN: 30, LEFT: 30}, **BOXED)[0], 0x40)
        # poorest 13 > 16 - 4: rest after the block; 21 + 7 + 5 * 3 + cmp, ja (taken) + mov, ret
        self.assertEqual(run(energy=16, en={UP: 13, RIGHT: 30, DOWN: 30, LEFT: 30}, **BOXED),
                         (REST, 47, 42))
        self.assertEqual(run(energy=46, en={UP: 42, RIGHT: 46, DOWN: 46, LEFT: 46}, **BOXED)[0], 0x40)
        self.assertEqual(run(energy=46, en={UP: 43, RIGHT: 46, DOWN: 46, LEFT: 46}, **BOXED)[0], REST)

    def test_capped_donor_and_never_into_47(self):
        self.assertEqual(run(energy=47, en={UP: 46, RIGHT: 47, DOWN: 47, LEFT: 47}, **BOXED)[0], 0x40)
        full = {UP: 47, RIGHT: 48, DOWN: 50, LEFT: 47}
        self.assertEqual(run(energy=50, en=full, **BOXED)[0], REST)
        self.assertEqual(run(energy=60, en=full, **BOXED)[0], REST)

    def test_feed_ignores_walls(self):
        v = dict(up=WA, right=WA, down=FR, left=WA)
        # 21 + 2 + 2 + 7 + 2 + cmp, ja + ret; taken: jz, jne x3
        self.assertEqual(run(energy=48, en={DOWN: 40}, **v), (0x42, 37, 33))
        self.assertEqual(run(energy=50, up=WA, right=WA, down=WA, left=WA)[0], REST)

    def test_boxed_cell_near_an_enemy_feeds(self):
        self.assertEqual(run(energy=30, far=8, en={UP: 10}, **BOXED)[0], 0x40)

    def test_params_factory(self):
        lazy = cells_ref.make_scourge(refill_min=16)
        self.assertEqual(lazy(FakeView(12, far=8, **ONLY[UP]), None)[0], REST)
        self.assertIs(policies.get('scourge'), policies.get('scourge'))
        self.assertEqual(policies.get('scourge[feed_d=20]')(FakeView(16, en={UP: 1}, **BOXED), None)[0], REST)


class ScourgeTableTest(unittest.TestCase):
    def test_tables_match_reference(self):
        g = load_gen()
        act, thr = g.refill_tables()
        enemy_sq = (6, 8, 10, 14, 16, 18)
        seen = 0
        for adj in itertools.product((EM, FR), repeat=4):
            for bits in range(64):
                far = [sq for k, sq in enumerate(enemy_sq) if bits >> k & 1]
                kw = dict(zip(('up', 'right', 'down', 'left'), adj))
                v = FakeView(0, far=far, **kw)
                m = g.refill_mask(v.cells)
                for e in (4, 11, 12, 15, 16, 50):
                    v.energy = e
                    a, n, _ = cells_ref.scourge(v, None)
                    if n == 11:
                        self.assertEqual((act[m], thr[m] <= e), (a, True), (adj, far, e))
                    else:
                        self.assertGreater(thr.get(m, 255), e, (adj, far, e))
                seen += 1
        self.assertEqual(seen, 1024)
        self.assertEqual(max(act), g.N_REFILL - 1)

    def test_source_rules(self):
        src = load_gen().generate()
        for bad in ('org ', 'bits ', 'section', '%include'):
            self.assertNotIn('\n' + bad, src.lower())
            self.assertNotIn('\t' + bad, src.lower())
        self.assertIn('Written with AI help', src)
        self.assertIn('Paste this whole file', src)
        self.assertLess(len(src.encode()), 64 * 1024)


class ScourgeMatchTest(unittest.TestCase):
    def test_short_match_without_faults(self):
        import bots
        eng = E.Engine([cells_ref.scourge, bots.hunter, bots.medic, bots.walker], width=32, height=32,
                       seed=3, max_ticks=300)
        eng.run()
        self.assertEqual(eng.faults[0], {})
        self.assertGreater(eng.pop[0], 1)


if __name__ == '__main__':
    unittest.main()
