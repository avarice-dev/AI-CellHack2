"""Tests of sim/cells_ref.py (Sprint reference policy) and of cells/gen_sprint.py's tables.

SprintPathTest: unit test of cells_ref.sprint; the view is faked.  Expected (action, insn, alt) values
were traced by hand from cells/sprint.asm (every executed instruction incl. taken jumps and ret; alt
leaves taken jumps out, the indirect jmp counting as taken).
SprintTableTest: unit test that the generator's tables agree with the reference for all 4^4 adjacent
type combinations (the reference is written independently of the tables).
SprintMatchTest: integration test, real engine + Sprint + real bots, nothing faked.
"""

import importlib.util
import itertools
import os
import unittest

from .helpers import E, SIM_DIR
import cells_ref

EM, FR, EN, WA = E.CELL_EMPTY, E.CELL_FRIEND, E.CELL_ENEMY, E.CELL_WALL
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3


def load_gen():
    path = os.path.join(os.path.dirname(SIM_DIR), 'cells', 'gen_sprint.py')
    spec = importlib.util.spec_from_file_location('gen_sprint', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeView(object):
    def __init__(self, energy, tick=0, up=EM, right=EM, down=EM, left=EM, far=None, self_type=FR):
        self.energy = energy
        self.tick = tick
        self.cells = [EM] * 25
        self.cells[12] = self_type
        self.cells[E.VIEW_UP] = up
        self.cells[E.VIEW_RIGHT] = right
        self.cells[E.VIEW_DOWN] = down
        self.cells[E.VIEW_LEFT] = left
        if far is not None:
            self.cells[far] = EN


def run(**kw):
    return cells_ref.sprint(FakeView(**kw), bytearray(64))


class SprintPathTest(unittest.TestCase):
    def test_bite_single(self):
        self.assertEqual(run(energy=0, up=EN), (0x30, 6, 5))
        self.assertEqual(run(energy=50, right=EN), (0x31, 6, 5))
        self.assertEqual(run(energy=3, down=EN), (0x32, 6, 5))
        self.assertEqual(run(energy=3, left=EN), (0x33, 6, 5))

    def test_bite_two_and_four_use_priority_down_left_up_right(self):
        self.assertEqual(run(energy=3, up=EN, right=EN)[0], 0x30)
        self.assertEqual(run(energy=3, up=EN, left=EN)[0], 0x33)
        self.assertEqual(run(energy=3, right=EN, down=EN)[0], 0x32)
        self.assertEqual(run(energy=3, up=EN, right=EN, down=EN, left=EN)[0], 0x32)

    def test_bite_three_goes_opposite_the_free_side(self):
        self.assertEqual(run(energy=3, right=EN, down=EN, left=EN)[0], 0x32)   # free UP -> DOWN
        self.assertEqual(run(energy=3, up=EN, down=EN, left=EN)[0], 0x33)      # free RIGHT -> LEFT
        self.assertEqual(run(energy=3, up=EN, right=EN, left=EN)[0], 0x30)     # free DOWN -> UP
        self.assertEqual(run(energy=3, up=EN, right=EN, down=EN)[0], 0x31)     # free LEFT -> RIGHT

    def test_rest_low_energy(self):
        self.assertEqual(run(energy=4), (E.ACT_REST, 8, 6))
        self.assertEqual(run(energy=0, far=0, tick=2999), (E.ACT_REST, 8, 6))

    def test_split_no_enemy_in_view(self):
        self.assertEqual(run(energy=5), (0x22, 19, 18))
        self.assertEqual(run(energy=5, down=FR), (0x21, 19, 18))
        self.assertEqual(run(energy=5, down=WA, right=FR), (0x20, 19, 18))
        self.assertEqual(run(energy=5, down=WA, right=FR, up=WA), (0x23, 19, 18))
        self.assertEqual(run(energy=50, down=WA, right=FR, up=WA, left=FR), (E.ACT_REST, 19, 18))

    def test_enemy_in_view(self):
        for far in (0, 4, 6, 8, 16, 18, 20, 24, 2, 10, 14, 22):
            self.assertEqual(run(energy=15, far=far), (E.ACT_REST, 20, 18), far)
            self.assertEqual(run(energy=16, far=far), (0x22, 21, 18), far)
            self.assertEqual(run(energy=5, far=far, tick=2980), (0x22, 23, 20), far)
        self.assertEqual(run(energy=15, far=0, tick=2979), (E.ACT_REST, 20, 18))

    def test_self_square_is_not_an_enemy(self):
        self.assertEqual(run(energy=10, self_type=EN), (0x22, 19, 18))


class SprintTableTest(unittest.TestCase):
    def test_tables_match_reference_for_all_adjacent_combinations(self):
        g = load_gen()
        fight, split = g.fight_table(), g.split_table()
        lane = {UP: 0, LEFT: 4, RIGHT: 6, DOWN: 10}
        for types in itertools.product((EM, FR, EN, WA), repeat=4):
            v = FakeView(50, **dict(zip(('up', 'right', 'down', 'left'), types)))
            act = cells_ref.sprint(v, bytearray(64))[0]
            emask = sum(1 << lane[d] for d in range(4) if types[d] == EN)
            if emask:
                self.assertEqual(act, 0x30 + fight[emask], types)
            else:
                mmask = sum(1 << lane[d] for d in range(4) if types[d] == EM)
                self.assertEqual(act, split[mmask], types)

    def test_table_sizes_and_reachable_masks(self):
        g = load_gen()
        self.assertEqual(g.N_MASKS, 1106)
        self.assertEqual(max(g.fight_table()), 0x451)
        self.assertEqual(len(g.fight_table()), 15)
        self.assertEqual(len(g.split_table()), 16)
        src = g.generate()
        for bad in ('org ', 'bits ', 'section', '%include'):
            self.assertNotIn('\n' + bad, src.lower())
            self.assertNotIn('\t' + bad, src.lower())
        self.assertLess(len(src.encode()), 64 * 1024)


class SprintMatchTest(unittest.TestCase):
    def test_short_match_without_faults(self):
        import bots
        eng = E.Engine([cells_ref.sprint, bots.hunter, bots.medic, bots.walker], width=32, height=32,
                       seed=3, max_ticks=300)
        eng.run()
        self.assertEqual(eng.faults[0], {})
        self.assertGreater(eng.pop[0], 1)


if __name__ == '__main__':
    unittest.main()
