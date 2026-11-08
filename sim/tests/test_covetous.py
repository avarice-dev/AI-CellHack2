"""Tests of sim/cells_ref.covetous (Covetous reference policy) and of cells/gen_covetous.py's tables.

CovetousPathTest: unit test of cells_ref.covetous; the view is faked.  Expected (action, insn, alt) values
were traced by hand from cells/gen_covetous.py's asm (every executed instruction incl. taken jumps and
ret; alt leaves taken jumps out).
CovetousTableTest: unit test that the generator's bite table agrees with the reference for all 4^4
adjacent type combinations, and that the source obeys the paste-into-the-site rules.
CovetousMatchTest: integration test, real engine + Covetous + real bots, nothing faked.
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


def load_gen():
    path = os.path.join(os.path.dirname(SIM_DIR), 'cells', 'gen_covetous.py')
    spec = importlib.util.spec_from_file_location('gen_covetous', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeView(object):
    def __init__(self, energy, tick=0, up=EM, right=EM, down=EM, left=EM, far=None, en=None):
        self.energy = energy
        self.tick = tick
        self.cells = [EM] * 25
        self.cells[12] = FR
        self.energies = [0] * 25
        for d, t in ((UP, up), (RIGHT, right), (DOWN, down), (LEFT, left)):
            self.cells[IDX[d]] = t
            if t in (FR, EN):
                self.energies[IDX[d]] = 20
        for d, v in (en or {}).items():
            self.energies[IDX[d]] = v
        if far is not None:
            self.cells[far] = EN


def run(**kw):
    return cells_ref.covetous(FakeView(**kw), bytearray(64))


BOXED = dict(up=FR, right=FR, down=FR, left=FR)


class CovetousPathTest(unittest.TestCase):
    def test_bite_is_5_in_every_direction(self):
        self.assertEqual(run(energy=0, up=EN), (0x30, 5, 4))
        self.assertEqual(run(energy=50, right=EN), (0x31, 5, 4))
        self.assertEqual(run(energy=3, down=EN), (0x32, 5, 4))
        self.assertEqual(run(energy=3, left=EN), (0x33, 5, 4))

    def test_multi_bite_choices_are_sprints(self):
        for types in itertools.product((EM, FR, EN, WA), repeat=4):
            if EN not in types:
                continue
            kw = dict(zip(('up', 'right', 'down', 'left'), types))
            self.assertEqual(run(energy=30, **kw)[:2], (cells_ref.sprint(FakeView(30, **kw), None)[0], 5))

    def test_rest_low_energy(self):
        self.assertEqual(run(energy=4), (E.ACT_REST, 9, 8))
        self.assertEqual(run(energy=0, far=0, tick=2999, **BOXED), (E.ACT_REST, 9, 8))

    def test_split_paths(self):
        self.assertEqual(run(energy=5), (0x22, 22, 22))
        self.assertEqual(run(energy=5, down=FR), (0x21, 22, 22))
        self.assertEqual(run(energy=16, far=0), (0x22, 24, 22))
        self.assertEqual(run(energy=5, far=24, tick=2980), (0x22, 26, 24))

    def test_feed_poorest_friend_when_boxed(self):
        # F = 20; feed block: +4, four friends at 20 -> first (UP) is new poorest (7), rest 5 each, feed +3
        self.assertEqual(run(energy=47, **BOXED), (0x40, 20 + 4 + 7 + 15 + 3, 20 + 4 + 7 + 15 + 3 - 4))
        # poorest is LEFT (ties go to the first in U, R, D, L)
        self.assertEqual(run(energy=50, en={LEFT: 5, DOWN: 9}, **BOXED)[0], 0x43)
        self.assertEqual(run(energy=50, en={RIGHT: 5, LEFT: 5}, **BOXED)[0], 0x41)

    def test_feed_only_near_cap_and_never_to_a_near_cap_friend(self):
        full = {UP: 47, RIGHT: 48, DOWN: 50, LEFT: 47}
        # rest after the block: 24 + 7 + 15, cmp, ja (taken), mov, ret; taken: jz, jae x3, ja
        self.assertEqual(run(energy=50, en=full, **BOXED), (E.ACT_REST, 24 + 7 + 15 + 4, 24 + 7 + 15 + 4 - 5))
        self.assertEqual(run(energy=46, en={UP: 1}, **BOXED), (E.ACT_REST, 24, 22))   # e < FEED_MIN 47
        self.assertEqual(run(energy=47, en={UP: 46, RIGHT: 47, DOWN: 47, LEFT: 47}, **BOXED)[0], 0x40)

    def test_feed_ignores_enemy_wall_empty(self):
        v = dict(up=WA, right=WA, down=FR, left=WA)
        self.assertEqual(run(energy=48, en={DOWN: 47}, **v)[0], E.ACT_REST)
        self.assertEqual(run(energy=48, en={DOWN: 40}, **v), (0x42, 20 + 4 + 2 + 2 + 7 + 2 + 3,
                                                              20 + 4 + 2 + 2 + 7 + 2 + 3 - 4))
        self.assertEqual(run(energy=50, up=WA, right=WA, down=WA, left=WA)[0], E.ACT_REST)
        # an empty neighbour means split, not feed
        self.assertEqual(run(energy=50, up=FR, en={UP: 1})[0], 0x22)

    def test_holding_cells(self):
        # enemy in view, e < 16, early: feed block at F = 19, but e < 47 -> rest
        self.assertEqual(run(energy=15, far=0, up=FR, en={UP: 4}), (E.ACT_REST, 23, 21))
        # enemy in view, e >= 16, boxed in: split finds no empty -> feed block at F = 22
        self.assertEqual(run(energy=47, far=0, en={UP: 10}, **BOXED), (0x40, 22 + 4 + 7 + 15 + 3,
                                                                        22 + 4 + 7 + 15 + 3 - 6))

    def test_params_factory(self):
        nofeed = cells_ref.make_covetous(feed_min=255)
        self.assertEqual(nofeed(FakeView(50, en={UP: 1}, **BOXED), None)[0], E.ACT_REST)
        self.assertIs(policies.get('covetous'), policies.get('covetous'))
        self.assertEqual(policies.get('covetous[feed_min=49]')(FakeView(48, en={UP: 1}, **BOXED), None)[0],
                         E.ACT_REST)


class CovetousTableTest(unittest.TestCase):
    def test_bite_table_matches_reference(self):
        g = load_gen()
        bite = g.bite_table()
        lane = {UP: 0, LEFT: 4, RIGHT: 6, DOWN: 10}
        for types in itertools.product((EM, FR, EN, WA), repeat=4):
            emask = sum(1 << lane[d] for d in range(4) if types[d] == EN)
            if emask:
                act = run(energy=50, **dict(zip(('up', 'right', 'down', 'left'), types)))[0]
                self.assertEqual(bite[emask], act, types)
        self.assertNotIn(0, bite)
        self.assertEqual(len(bite), 15)

    def test_source_rules(self):
        src = load_gen().generate()
        for bad in ('org ', 'bits ', 'section', '%include'):
            self.assertNotIn('\n' + bad, src.lower())
            self.assertNotIn('\t' + bad, src.lower())
        self.assertIn('Written with AI help', src)
        self.assertLess(len(src.encode()), 64 * 1024)


class CovetousMatchTest(unittest.TestCase):
    def test_short_match_without_faults(self):
        import bots
        eng = E.Engine([cells_ref.covetous, bots.hunter, bots.medic, bots.walker], width=32, height=32,
                       seed=3, max_ticks=300)
        eng.run()
        self.assertEqual(eng.faults[0], {})
        self.assertGreater(eng.pop[0], 1)


if __name__ == '__main__':
    unittest.main()
