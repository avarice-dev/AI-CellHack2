"""Race recorder (Engine record_races=True): one row per death, like tools/pull2/mine.py's races CSV.

Integration tests of engine.py with scripted policies (nothing of ours faked).
Row: (tDeath, deadCol, killerCol, contMask, fillCol, dt, fillKind, fillE); fillKind 1 birth, 2 move,
0 unfilled at the end (fillCol -1, dt = ticks left, fillE -1).
"""

import unittest

from .helpers import E, board, script, eat, split, move, REST, RIGHT, LEFT, UP, DOWN, NOP


class RaceRecorderTest(unittest.TestCase):
    def test_off_by_default(self):
        e = board([script({})])
        self.assertIsNone(e.races)

    def test_death_then_birth_refill_next_tick(self):
        # colony 1 at (2,2) kills colony 0's 2-energy cell at (1,2) in tick 0; in tick 1 colony 0's
        # cell at (0,2) splits into (1,2).  Contenders at death: (0,2) colony 0, (2,2) colony 1.
        p0 = script({(1, 0, 2): (split(RIGHT), 3)}, default=(REST, 9))
        p1 = script({(0, 2, 2): (eat(LEFT), 1)}, default=(REST, 9))
        e = board([p0, p1], record_races=True)
        e.add_cell(0, 2, 0, 10)
        e.add_cell(1, 2, 0, 2)
        e.add_cell(2, 2, 1, 10)
        e.step()
        e.step()
        self.assertEqual(e.race_rows(), [(0, 0, 1, 0b11, 0, 1, 1, 5)])

    def test_move_refill_and_censored(self):
        # tick 0: colony 1 kills (1,1) (energy 1) and colony 0 kills colony 1's (3,3) energy-2 cell.
        # tick 1: colony 1's (2,1) moves left into (1,1).  (3,3) stays empty: censored at the end.
        p0 = script({(0, 3, 2): (eat(DOWN), 1)}, default=(REST, 9))
        p1 = script({(0, 2, 1): (eat(LEFT), 1), (1, 2, 1): (move(LEFT), 1)}, default=(REST, 9))
        e = board([p0, p1], record_races=True)
        e.add_cell(1, 1, 0, 1)
        e.add_cell(2, 1, 1, 7)
        e.add_cell(3, 2, 0, 10)
        e.add_cell(3, 3, 1, 2)
        e.step()
        e.step()
        e.step()
        rows = e.race_rows()
        self.assertIn((0, 0, 1, 0b10, 1, 1, 2, 8), rows)    # mover's start-of-tick energy 7 + 1 rest = 8
        self.assertIn((0, 1, 0, 0b01, -1, 3, 0, -1), rows)
        self.assertEqual(len(rows), 2)

    def test_killer_is_last_eater(self):
        # colony 1 bites at tick 0 (10 -> 8), colony 2 kills at... use a 3-energy cell: c1 bites (3->1),
        # c2 bites next tick (1->0): killer = colony 2.
        p0 = script({}, default=(REST, 99))
        p1 = script({(0, 0, 1): (eat(RIGHT), 1)}, default=(REST, 9))
        p2 = script({(1, 2, 1): (eat(LEFT), 1)}, default=(REST, 9))
        e = board([p0, p1, p2], record_races=True)
        e.add_cell(1, 1, 0, 2)
        e.add_cell(0, 1, 1, 10)
        e.add_cell(2, 1, 2, 10)
        e.c_en[e.cell_at(1, 1)] = 3
        e.step()
        e.step()
        rows = e.race_rows()
        self.assertEqual([r[:4] for r in rows], [(1, 0, 2, 0b110)])


if __name__ == '__main__':
    unittest.main()
