"""Tests of Penalty (Conviction, and the queue ends with a split into the target's square).

PenaltyRefTest: unit test of sim/cells_ref.make_penalty; the view and the memory are faked.  Expected queues are
written from the spec in cells/gen_penalty.py's docstring, not from the policy.
PenaltyGenTest: unit test of cells/gen_penalty.py: the committed asm is the generator's output; table values.
PenaltyEngineTest: integration test, real engine, the Penalty policy against a resting policy on a small board: a
Penalty cell kills a thin resting enemy and has a second cell one tick later (the queued split).
"""

import os
import sys
import unittest

from .helpers import E
import cells_ref
from .test_bane2 import View, mem, UP, RIGHT, DOWN, LEFT, EM, FR, EN, WA, MOVE, SPLIT, REST, CELLS_DIR

EAT = 0x30


def plan(m):
    q = [b for b in m[9:16]]
    while q and q[-1] == 0:
        q.pop()
    return q


class PenaltyRefTest(unittest.TestCase):
    def setUp(self):
        self.p = cells_ref.make_penalty()

    def scan(self, te, d=RIGHT):
        adj = [EM] * 4
        adj[d] = EN
        v = View(20, adj)
        v.energies[(7, 13, 17, 11)[d]] = te
        m = mem(bear=LEFT, steps=0, pos=(10, 10))
        act, n = self.p(v, m)[:2]
        self.assertEqual((act, n), (EAT + d, 18))
        self.assertEqual(m[8], 0)
        return plan(m)

    def test_kill_now_queues_the_split(self):
        for te in (1, 2):
            self.assertEqual(self.scan(te), [SPLIT + RIGHT])

    def test_predicted_kill_ends_with_the_split(self):
        e, s = EAT + DOWN, SPLIT + DOWN
        self.assertEqual(self.scan(3, DOWN), [e, s])
        self.assertEqual(self.scan(4, DOWN), [e, s])
        self.assertEqual(self.scan(5, DOWN), [e, e, s])
        self.assertEqual(self.scan(8, DOWN), [e, e, e, s])

    def test_fat_target_gets_bites_only(self):
        e = EAT + UP
        self.assertEqual(self.scan(9, UP), [e] * 4)
        self.assertEqual(self.scan(20, UP), [e] * 7)
        self.assertEqual(self.scan(50, UP), [e] * 7)

    def test_queue_plays_in_three_instructions_then_empties(self):
        m = mem(bear=LEFT, steps=0, pos=(10, 10))
        v = View(20, (EM, EN, EM, EM))
        v.energies[13] = 4
        self.p(v, m)
        self.assertEqual(self.p(View(20), m), (EAT + RIGHT, 3, 2))
        self.assertEqual(self.p(View(20), m), (SPLIT + RIGHT, 3, 2))
        act, n = self.p(View(3), m)[:2]                                 # queue empty: normal paths
        self.assertEqual(act, REST)
        self.assertEqual(n, cells_ref.bane2.core(View(3), mem(bear=LEFT, steps=0, pos=(10, 10)))[1] + 3)

    def test_other_paths_are_convictions(self):
        for v in (View(16), View(12, far=(6,)), View(30, (FR, FR, FR, FR)), View(2), View(5), View(9, far=(6,))):
            m1, m2 = mem(bear=RIGHT, steps=4, pos=(10, 10)), mem(bear=RIGHT, steps=4, pos=(10, 10))
            self.assertEqual(self.p(v, m1), cells_ref.conviction(v, m2))
            self.assertEqual(bytes(m1), bytes(m2))


class PenaltyGenTest(unittest.TestCase):
    def test_committed_asm_is_the_generator_output(self):
        sys.path.insert(0, CELLS_DIR)
        import gen_penalty
        with open(os.path.join(CELLS_DIR, 'penalty.asm'), newline='') as f:
            self.assertEqual(f.read(), gen_penalty.generate())

    def test_queue_values(self):
        sys.path.insert(0, CELLS_DIR)
        import gen_penalty as P
        self.assertEqual(P.queue_value(1, 2), 0x2100)
        self.assertEqual(P.queue_value(1, 4), 0x213100)
        self.assertEqual(P.queue_value(0, 63), 0x3030303030303000)
        self.assertEqual(P.queue_plan(2, 0), [0x22])


class PenaltyEngineTest(unittest.TestCase):
    def test_kills_a_thin_rester_and_takes_its_square(self):
        def rester(view, m):
            return E.ACT_REST, 30                                       # slower than any Penalty path used here
        eng = E.Engine([cells_ref.penalty, rester], width=8, height=8, seed=1, max_ticks=10, place_start=False)
        eng.add_cell(3, 3, 0, energy=30)
        eng.add_cell(4, 3, 1, energy=2)
        eng.add_cell(7, 7, 1, energy=30)                                # keeps the match alive after the kill
        eng.step()
        self.assertEqual((eng.pop[0], eng.pop[1]), (1, 1))              # tick 0: the bite killed the thin cell
        eng.step()
        self.assertEqual(eng.pop[0], 2)                                 # tick 1: the queued split took its square

if __name__ == '__main__':
    unittest.main()
