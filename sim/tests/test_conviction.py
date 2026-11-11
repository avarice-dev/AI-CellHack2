"""Tests of Conviction (Bane v2.2 with a bite queue).

ConvictionRefTest: unit test of sim/cells_ref.make_conviction; the view and the memory are faked.  Expected values
are written from the spec in cells/gen_conviction.py's docstring, not from the policy.
ConvictionGenTest: unit test of cells/gen_conviction.py: the committed asm is the generator's output; paste rules.
ConvictionSoloTest: integration test, real engine, one colony: the opening is Bane v2.2's (no enemy, no queue).
"""

import os
import sys
import unittest

from .helpers import E
import cells_ref
from .test_bane2 import View, mem, UP, RIGHT, DOWN, LEFT, EM, FR, EN, WA, MOVE, SPLIT, REST, CELLS_DIR

EAT = 0x30


def queue(m):
    return [b for b in m[8:16]]


class ConvictionRefTest(unittest.TestCase):
    def setUp(self):
        self.p = cells_ref.make_conviction()

    def view(self, energy, adj, target_energy):
        v = View(energy, adj)
        for i, t in zip((7, 13, 17, 11), adj):
            if t == EN:
                v.energies[i] = target_energy
        return v

    def test_scan_bite_queues_what_the_target_survives(self):
        # energy <= 2: this bite kills it, nothing queued.  Else what an unfed target still needs, (e + 1) // 2 - 1,
        # but at least 3 (it may be fed from behind) and at most 7
        for te, n in ((1, 0), (2, 0), (3, 3), (4, 3), (6, 3), (8, 3), (9, 4), (10, 4), (15, 7), (18, 7), (50, 7)):
            m = mem(bear=LEFT, steps=0, pos=(10, 10))
            act, cnt = self.p(self.view(20, (EM, EN, EM, EM), te), m)[:2]
            self.assertEqual((act, cnt), (EAT + RIGHT, 19))
            self.assertEqual(queue(m), [0] + [EAT + RIGHT] * n + [0] * (7 - n), te)

    def test_queued_bites_play_without_looking(self):
        m = mem(bear=LEFT, steps=0, pos=(10, 10))
        self.p(self.view(20, (EN, EM, EM, EM), 5), m)                   # queue 3 bites UP
        gone = View(20, (FR, EM, EM, EM))                               # the view no longer matters
        for _ in range(3):
            self.assertEqual(self.p(gone, m), (EAT + UP, 3, 2))
        act, cnt = self.p(gone, m)[:2]                                  # queue empty: the normal paths again
        self.assertEqual(act & 0xF0, SPLIT)
        self.assertEqual(cnt, cells_ref.bane2.core(gone, bytearray(64))[1] + 3)
        self.assertEqual(queue(m), [0] * 8)

    def test_other_paths_are_bane22_plus_three(self):
        for v in (View(16), View(12, far=(6,)), View(3, (FR, FR, FR, WA)), View(30, (FR, FR, FR, FR)),
                  View(2), View(5), View(9, far=(6,))):
            m1, m2 = mem(bear=RIGHT, steps=4, pos=(10, 10)), mem(bear=RIGHT, steps=4, pos=(10, 10))
            a, n, t = cells_ref.bane2.core(v, m1)
            self.assertEqual(self.p(v, m2), (a, n + 3, t + 3))
            self.assertEqual(bytes(m1), bytes(m2))

    def test_a_child_never_inherits_a_queue(self):
        # any call that splits has an empty queue after it
        m = mem(bear=UP, steps=0, pos=(10, 10))
        m[9] = EAT + DOWN                                               # one queued bite left
        self.assertEqual(self.p(View(5), m)[0], EAT + DOWN)
        self.assertEqual(self.p(View(5), m)[0] & 0xF0, SPLIT)
        self.assertEqual(queue(m), [0] * 8)


class ConvictionGenTest(unittest.TestCase):
    def test_committed_asm_is_the_generator_output(self):
        sys.path.insert(0, CELLS_DIR)
        import gen_conviction
        with open(os.path.join(CELLS_DIR, 'conviction.asm'), newline='') as f:
            self.assertEqual(f.read(), gen_conviction.generate())

    def test_tables(self):
        sys.path.insert(0, CELLS_DIR)
        import gen_conviction as C
        self.assertEqual([C.queue_len(e) for e in (0, 2, 3, 4, 8, 9, 14, 15, 63)], [0, 0, 3, 3, 3, 4, 6, 7, 7])
        self.assertEqual(C.queue_value(2, 0), 0)
        self.assertEqual(C.queue_value(1, 2), 0x313100)

    def test_paste_rules(self):
        with open(os.path.join(CELLS_DIR, 'conviction.asm')) as f:
            code = '\n'.join(l.split(';')[0] for l in f.read().splitlines())
        for word in ('org ', 'bits ', 'section', '%include', 'rdx', 'setlock', 'lock_off'):
            self.assertNotIn(word, code)


class ConvictionSoloTest(unittest.TestCase):
    def test_solo_opening_equals_bane22(self):
        def run(pol):
            eng = E.Engine([pol], seed=3, max_ticks=60, start_mode='fixed', start_positions=[(30, 31)])
            while eng.step():
                pass
            return eng.pop[0]
        self.assertEqual(run(cells_ref.conviction), run(cells_ref.bane2))


if __name__ == '__main__':
    unittest.main()
