"""Tests of Depravity (planned): Misfortune (cap B, exact 1) + hold='split' (hold_min 10) + the CHECKED REFILL.

Unit tests of sim/cells_ref.make_depravity (one module, no I/O); view and memory are faked.
Checked refill: a bite (slow path returning EAT + d beside an enemy) stores SPLIT + d in byte 2 (0 = none; byte 2 is free
in Misfortune and the prefix clean, bytes 9+, never touches it).  On the next slow path, right after the prefix clean:
if byte 2 is set and the snapshot square in that direction is EMPTY and own energy >= 12, return SPLIT + d; either way the
byte is cleared first (so a child, which copies memory after the call, starts with 0).  Armed slots are Misfortune's own.
Counts: fire path 13 (prefix 4 + 9); no stored dir: normal path + 2; stored dir, square taken: + 7; stored dir, e < 12: + 9;
the biting / arming path: Misfortune's count + 4 (or, jz, and the 2-instruction word store).
"""

import unittest

import cells_ref
from .test_bane2 import View, mem, UP, RIGHT, DOWN, LEFT, EM, FR, EN
from .test_misfortune import armed_view, slots, SLOT0, SPLIT_K

DEP = cells_ref.make_depravity
BASE = lambda: cells_ref.make_misfortune(cap='B', exact=1, hold='split', hold_min=10)
SPLIT = SPLIT_K


def refill_view(e, d, occupant=EM):
    adj = [EM, EM, EM, EM]
    adj[d] = occupant
    return View(e, tuple(adj))


class DepravityTest(unittest.TestCase):
    def test_registered(self):
        self.assertIs(cells_ref.FACTORIES['depravity'], cells_ref.make_depravity)

    def test_stored_dir_written_on_bite(self):
        for d in range(4):
            for te in (1, 2, 5, 20):
                m = mem()
                act, n, t = DEP()(armed_view(20, te=te, d=d), m)
                self.assertEqual(m[2], SPLIT + d, (d, te))
                self.assertEqual(act & 3, d)

    def test_armed_slots_are_misfortunes_row(self):
        for e0 in (5, 12, 20, 40, 48, 49, 50):
            for d in range(4):
                for te in (1, 2, 3, 9, 50):
                    a, b = mem(), mem()
                    DEP()(armed_view(e0, te=te, d=d), a)
                    BASE()(armed_view(e0, te=te, d=d), b)
                    self.assertEqual(slots(a), slots(b), (e0, d, te))
                    self.assertEqual(a[8], b[8])
                    self.assertTrue(all(v & 0xF0 == 0x30 for v in slots(a).values()))   # no SPLIT in any slot

    def test_refill_fires_on_empty(self):
        for d in range(4):
            for e in (12, 20, 50):
                m = mem(); m[2] = SPLIT + d
                self.assertEqual(DEP()(refill_view(e, d), m), (SPLIT + d, 13, 13), (d, e))

    def test_occupied_square_never_refilled(self):
        for occ in (EN, FR):
            for d in range(4):
                for e in (12, 30):
                    m = mem(); m[2] = SPLIT + d
                    act = DEP()(refill_view(e, d, occ), m)[0]
                    # the stored action must not be played blindly into an occupied square
                    if occ == FR:
                        self.assertNotEqual(act, SPLIT + d)

    def test_below_12_no_refill(self):
        for e in range(0, 12):
            m = mem(); m[2] = SPLIT + RIGHT
            act, n, t = DEP()(refill_view(e, RIGHT), m)
            self.assertEqual(m[2], 0)                   # cleared, normal path
            ref = BASE()(refill_view(e, RIGHT), mem())
            self.assertEqual((act, n), (ref[0], ref[1] + 9), e)

    def test_byte_cleared_so_child_starts_clean(self):
        m = mem(); m[2] = SPLIT + UP
        DEP()(refill_view(30, UP), m)
        self.assertEqual(m[2], 0)
        m = mem(); m[2] = SPLIT + UP
        DEP()(refill_view(30, UP, FR), m)
        self.assertEqual(m[2], 0)

    def test_counts(self):
        ref = BASE()(refill_view(30, UP, FR), mem())
        m = mem()
        r = DEP()(refill_view(30, UP, FR), m)
        self.assertEqual(r[1], ref[1] + 2)                 # none stored: or, jz
        m = mem(); m[2] = SPLIT + UP
        r = DEP()(refill_view(30, UP, FR), m)
        self.assertEqual(r[1], ref[1] + 7)                 # stored dir, square taken
        b = BASE()(armed_view(20, te=9), mem())
        self.assertEqual(DEP()(armed_view(20, te=9), mem())[1], b[1] + 4)   # biting path: or, jz + word store (2)
        m = mem(); m[SLOT0 + 21] = 0x33
        self.assertEqual(DEP()(View(21, (EM, EM, EM, EM)), m), (0x33, 2, 1))   # armed bite stays 2


if __name__ == '__main__':
    unittest.main()
