"""Tests of Depravity (planned): Misfortune (cap B, exact 1) + hold='split' (hold_min 10) + the ARMED REFILL.

Unit tests of sim/cells_ref.make_depravity (one module, no I/O); view and memory are faked.
Armed refill: when the biter sees its target at <= 2 energy (this bite kills it) and its own energy e0 >= 12, it arms
slot row (slot = byte 13 + energy): SPLIT + d at e0 + 1, e0 + 2 and e0 - 1; EAT + d at e0 - 2 and e0 - 4; 0 everywhere
else (slot e0 and e0 - 3 included; slot 50 never armed).  Below e0 12 nothing is armed.  Target at 3+ energy: exactly
Misfortune's row.  The expected rows below are written out from this spec, not taken from cells_ref.
"""

import unittest

import cells_ref
from .test_bane2 import View, mem, UP, RIGHT, DOWN, LEFT, EM, EN
from .test_misfortune import armed_view, slots, Spy, SLOT0, EAT, SPLIT_K

DEP = cells_ref.make_depravity
SPLIT = SPLIT_K


def expected_row(e0, d):
    row = {e0 - 4: EAT + d, e0 - 2: EAT + d, e0 - 1: SPLIT + d, e0 + 1: SPLIT + d, e0 + 2: SPLIT + d}
    return {s: a for s, a in row.items() if 0 <= s <= 49}      # slot 50 stays 0; > 50 is not a slot


class DepravityTest(unittest.TestCase):
    def test_registered(self):
        self.assertIs(cells_ref.FACTORIES['depravity'], cells_ref.make_depravity)

    def test_row_for_dying_target(self):
        for e0 in (12, 13, 20, 31, 40, 47, 48, 49, 50):
            for d in range(4):
                for te in (1, 2):
                    m = mem()
                    act, n, t = DEP()(armed_view(e0, te=te, d=d), m)
                    self.assertEqual(act, EAT + d)
                    self.assertEqual(slots(m), expected_row(e0, d), (e0, d, te))
                    self.assertEqual(m[8], e0)

    def test_named_energies(self):
        for e0 in (12, 20, 40, 48, 49, 50):
            m = mem()
            DEP()(armed_view(e0, te=2, d=RIGHT), m)
            self.assertEqual(m[SLOT0 + e0], 0)             # slot e0: my bite failed, rescan
            self.assertEqual(m[SLOT0 + e0 - 3], 0)
            self.assertEqual(m[63], 0)                     # slot 50 never armed
            self.assertEqual(m[SLOT0 + e0 - 1], SPLIT + RIGHT)
            self.assertEqual(m[SLOT0 + e0 - 4], EAT + RIGHT)
            self.assertEqual(m[SLOT0 + e0 - 2], EAT + RIGHT)

    def test_nothing_armed_below_12(self):
        for e0 in range(0, 12):
            for d in range(4):
                m = mem()
                DEP()(armed_view(e0, te=2, d=d), m)
                self.assertEqual(slots(m), {}, (e0, d))

    def test_slot50_and_stores_inside_memory(self):
        for e0 in range(12, 51):
            for d in range(4):
                m = Spy(mem())
                DEP()(armed_view(e0, te=1, d=d), m)
                self.assertTrue(all(0 <= i < 64 for i in m.writes), (e0, d))
                self.assertEqual(bytearray.__getitem__(m, 63), 0)

    def test_armed_slots_inside_prefix_window(self):
        for e0 in range(12, 51):
            for s in expected_row(e0, 0):
                self.assertTrue(e0 - 4 <= s <= e0 + 10)    # the next slow tick's prefix zeroes bytes 9+e0..24+e0

    def test_target_3_plus_keeps_misfortune_row(self):
        for e0 in (5, 12, 20, 40, 49, 50):
            for d in range(4):
                for te in (3, 4, 5, 9, 20, 50):
                    a, b = mem(), mem()
                    ra = DEP()(armed_view(e0, te=te, d=d), a)
                    rb = cells_ref.make_misfortune(cap='B', exact=1, hold='split', hold_min=10)(
                        armed_view(e0, te=te, d=d), b)
                    self.assertEqual(bytes(a), bytes(b), (e0, d, te))
                    self.assertEqual(ra, rb)

    def test_counts(self):
        # armed path stays 2; the arming path of a dying target pays the e0 test (assumed cmp / jb = +2)
        m2 = mem(); m2[SLOT0 + 21] = SPLIT + RIGHT
        self.assertEqual(DEP()(View(21, (EM, EM, EM, EM)), m2), (SPLIT + RIGHT, 2, 1))
        self.assertEqual(DEP()(armed_view(20, te=2), mem())[1:], (21, 20))
        self.assertEqual(DEP()(armed_view(8, te=2), mem())[1:], (21, 20))
        self.assertEqual(DEP()(armed_view(20, te=9), mem())[1:], (19, 18))


if __name__ == '__main__':
    unittest.main()
