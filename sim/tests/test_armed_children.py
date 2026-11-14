"""Tests of armed children (reference only, no asm yet): make_misfortune2(armed_children=True).

Unit tests of sim/cells_ref (one module, no I/O); view and memory are faked.  Engine facts (sim/engine.py, ACT_SPLIT):
the child gets e // 2, the parent keeps the rest, the child's memory is a copy of the parent's AFTER the call, the child
takes no turn on its birth tick.  Armed only for e = 1 mod 4: the child (c = e // 2, even) takes the slots on even energies; the parent after the split
(c + 1) and after a failed split (e) are odd and move by -2 / +2 only, so it never reads one.
"""

import unittest

import cells_ref
from .test_bane2 import View, mem, UP, RIGHT, DOWN, LEFT, EM, FR, EN, IDX
from .test_misfortune import SPLIT_K

EAT = 0x30
OFF = (-5, 1, 5, -1)
AC = lambda **kw: cells_ref.make_misfortune2(armed_children=True, **kw)
PLAIN = lambda **kw: cells_ref.make_misfortune2(**kw)
SLOT0 = 13


def split_view(e, ds=UP, enemies=(), friends=()):
    """Parent at the centre, only the square in direction ds empty, enemies / friends on neighbours of that square."""
    adj = [FR, FR, FR, FR]
    adj[ds] = EM
    far = []
    v = View(e, tuple(adj), far=tuple(IDX[ds] + OFF[d] for d in enemies))
    for d in friends:
        v.cells[IDX[ds] + OFF[d]] = FR
        v.energies[IDX[ds] + OFF[d]] = 20
    return v


def armed_slots(m):
    return {i - SLOT0: m[i] for i in range(SLOT0 - 4, 64) if m[i]}


class ArmedChildrenTest(unittest.TestCase):
    def test_armed_toward_the_enemy_beside_the_child(self):
        for ds in range(4):
            for de in range(4):
                if de == (ds + 2) & 3:
                    continue                                   # that neighbour is the parent
                for e in (17, 25, 49):
                    m = mem()
                    act = AC()(split_view(e, ds, enemies=(de,)), m)[0]
                    self.assertEqual(act, SPLIT_K + ds, (ds, de, e))
                    c = e // 2
                    self.assertEqual(m[8], c)
                    self.assertEqual(armed_slots(m), {s: EAT + de for s in range(c - 4, c + 11, 2) if s >= 0}, (ds, de, e))

    def test_two_enemies_use_the_bite_priority(self):
        m = mem()
        AC()(split_view(17, UP, enemies=(LEFT, RIGHT)), m)
        self.assertEqual(set(armed_slots(m).values()), {EAT + cells_ref._sprint_bite({LEFT, RIGHT})})

    def test_never_armed_toward_a_friend(self):
        m = mem()
        AC()(split_view(17, UP, friends=(UP, LEFT, RIGHT)), m)
        self.assertEqual(armed_slots(m), {})
        m = mem()
        AC()(split_view(17, UP, enemies=(RIGHT,), friends=(UP, LEFT)), m)
        self.assertEqual(set(armed_slots(m).values()), {EAT + RIGHT})

    def test_nothing_armed_without_an_enemy_beside_the_child(self):
        for e in range(5, 50, 2):
            m = mem()
            self.assertEqual(armed_slots(m), {})
            AC()(split_view(e, UP), m)
            self.assertEqual(armed_slots(m), {}, e)
            self.assertEqual(m[8], 0)

    def test_other_energies_stay_unarmed(self):
        for e in range(5, 50):
            if e % 4 == 1:
                continue                                       # armed: e = 1 mod 4 (c even; see cells_ref)
            m = mem()
            AC()(split_view(e, DOWN, enemies=(LEFT,)), m)
            self.assertEqual(armed_slots(m), {}, e)

    def test_parent_never_reads_a_child_slot(self):
        armed = 0
        for e in range(5, 50, 2):
            for ds in range(4):
                for de in range(4):
                    if de == (ds + 2) & 3:
                        continue
                    m = mem()
                    r = AC()(split_view(e, ds, enemies=(de,)), m)
                    if r[0] != SPLIT_K + ds or not armed_slots(m):
                        continue
                    armed += 1
                    c, parent = e // 2, e - e // 2
                    self.assertEqual(parent, c + 1)
                    # the parent's energy after any run of bites (-2) and feeds (+2), after the split (c + 1) or after a
                    # failed split (it keeps e): all odd, never a slot
                    self.assertEqual({parent % 2, e % 2}, {1})
                    for pe in range(1, 51, 2):
                        self.assertEqual(m[SLOT0 + pe], 0, (e, ds, de, pe))
                    self.assertTrue(all((s - c) % 2 == 0 for s in armed_slots(m)))
                    # its next call (energy c + 1) is a slow path: the prefix zeroes every armed slot (byte 8 = c)
                    nxt = mem(); nxt[:] = m
                    PLAIN()(View(parent, (FR, FR, FR, FR)), nxt)
                    self.assertEqual(armed_slots(nxt), {}, (e, ds, de))
        self.assertGreater(armed, 50)

    def test_child_copy_plays_the_bite_on_its_first_call(self):
        m = mem()
        AC()(split_view(17, UP, enemies=(RIGHT,)), m)
        child_mem = bytearray(m)                                # the engine copies the memory after the call
        for ce in (8, 6, 4):                                    # born at 8, or bitten once / twice before its call
            self.assertEqual(PLAIN()(View(ce, (EN, FR, FR, FR)), bytearray(child_mem))[:2], (EAT + RIGHT, 2))

    def test_refill_path_is_not_changed(self):
        m = mem(); m[2] = SPLIT_K + UP
        r = AC()(split_view(21, UP, enemies=(RIGHT,)), m)
        self.assertEqual(r[:2], (SPLIT_K + UP, 13))
        self.assertEqual(armed_slots(m), {})

    def test_other_paths_equal_plain(self):
        for e in (4, 12, 30):
            v = View(e, (EN, EM, FR, FR))
            a, b = mem(), mem()
            self.assertEqual(AC()(v, a), PLAIN()(v, b))
            self.assertEqual(a, b)

    def test_extra_instruction_counts(self):
        # open space, gate 1 not freed (e = 17, no enemy anywhere): only the flag test (+2), on any e mod 4
        for e in (17, 19):
            v = split_view(e, UP)
            self.assertEqual(AC()(v, mem())[1] - PLAIN()(v, mem())[1], cells_ref.ARMCHILD_FLAG_N)
        # freed gate-1 split (enemy proven near): no flag test; e = 1 mod 4 pays mod4 + scan + store, 3 mod 4 only mod4
        for e, extra in ((17, 3 + 8 + 10), (19, 3)):
            v = split_view(e, UP, enemies=(RIGHT,))
            self.assertEqual(AC()(v, mem())[1] - PLAIN()(v, mem())[1], extra, e)


if __name__ == '__main__':
    unittest.main()
