"""Tests of sim/rivals.py (rival reference policies).

RivalPathTest classes: unit tests, the view is faked.  Expected (action, insn, alt) values come from the
asm sketches in rivals.py's comments (every executed instruction incl. taken jumps and ret; alt leaves
taken jumps out, the indirect `jmp [table]` counting as taken).
RivalMatchTest: integration test, real engine + rivals + bots, nothing faked.
"""

import unittest

from .helpers import E
import rivals
import policies

EM, FR, EN, WA = E.CELL_EMPTY, E.CELL_FRIEND, E.CELL_ENEMY, E.CELL_WALL
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
REST = E.ACT_REST
NB = {UP: 7, RIGHT: 13, DOWN: 17, LEFT: 11}
FAR = {UP: 2, RIGHT: 14, DOWN: 22, LEFT: 10}


class FakeView(object):
    def __init__(self, energy, rand=0, tick=0, fill=EM, fill_e=0, cells=None, energies=None):
        self.energy = energy
        self.rand = rand
        self.tick = tick
        self.cells = [fill] * 25
        self.energies = [fill_e if fill == FR else 0] * 25
        self.cells[12] = FR
        self.energies[12] = energy
        for i, t in (cells or {}).items():
            self.cells[i] = t
            if t != FR:
                self.energies[i] = 0 if t in (EM, WA) else 10
        for i, v in (energies or {}).items():
            self.energies[i] = v


def nb(**kw):
    """{'up': EN, ...} -> {7: EN, ...}"""
    names = {'up': UP, 'right': RIGHT, 'down': DOWN, 'left': LEFT}
    return {NB[names[k]]: v for k, v in kw.items()}


def lock_byte(d):
    return 1 + d


class Lock5Test(unittest.TestCase):
    pol = staticmethod(rivals.rlock5)

    def call(self, view, mem=None):
        mem = bytearray(64) if mem is None else mem
        return self.pol(view, mem), mem

    def test_locked_bite_is_5(self):
        mem = bytearray(64)
        mem[0] = lock_byte(RIGHT)
        r, _ = self.call(FakeView(3, cells=nb(right=EN)), mem)
        self.assertEqual(r, (0x31, 5, 5))

    def test_unlocked_bite_is_10_and_sets_lock(self):
        for d in range(4):
            r, mem = self.call(FakeView(3, cells={NB[d]: EN}))
            self.assertEqual(r, (0x30 + d, 10, 8))
            self.assertEqual(mem[0], lock_byte(d))

    def test_stale_lock_falls_through_and_relocks(self):
        mem = bytearray(64)
        mem[0] = lock_byte(RIGHT)
        r, mem = self.call(FakeView(3, cells=nb(up=EN, right=FR)), mem)
        self.assertEqual(r, (0x30, 10, 8))
        self.assertEqual(mem[0], lock_byte(UP))

    def test_multi_enemy_uses_f6_priority(self):
        r, _ = self.call(FakeView(3, cells=nb(up=EN, left=EN)))
        self.assertEqual(r[0], 0x33)           # Sprint/F6 priority DOWN, LEFT, UP, RIGHT

    def test_rest_below_5(self):
        r, mem = self.call(FakeView(4))
        self.assertEqual(r, (REST, 19, 16))
        self.assertEqual(mem[0], 0)

    def test_prearm_far_enemy_sets_lock_then_first_contact_is_5(self):
        for d in range(4):
            r, mem = self.call(FakeView(4, cells={FAR[d]: EN}))
            self.assertEqual(r, (REST, 21, 16))
            self.assertEqual(mem[0], lock_byte(d))
            r2, _ = self.call(FakeView(4, cells={NB[d]: EN}), mem)
            self.assertEqual(r2, (0x30 + d, 5, 5))

    def test_prearm_priority_up_left_right_down(self):
        _, mem = self.call(FakeView(4, cells={FAR[DOWN]: EN, FAR[RIGHT]: EN, FAR[LEFT]: EN}))
        self.assertEqual(mem[0], lock_byte(LEFT))

    def test_split_at_5_into_empty_from_rand_rotation(self):
        r, _ = self.call(FakeView(5, rand=0))
        self.assertEqual(r, (0x20, 27, 25))
        r, _ = self.call(FakeView(5, rand=2, cells=nb(down=FR)))
        self.assertEqual(r[0], 0x23)           # start at DOWN, taken, next LEFT
        r, _ = self.call(FakeView(9, rand=0, cells={FAR[UP]: EN}))
        self.assertEqual(r, (0x20, 29, 25))    # armed on the way

    def test_no_empty_below_6_rests(self):
        r, _ = self.call(FakeView(5, fill=FR, fill_e=5))
        self.assertEqual(r, (REST, 26, 22))

    def test_feeds_poorest_friend_first_in_urdl_order_on_ties(self):
        v = FakeView(10, fill=FR, fill_e=20, energies={7: 9, 13: 5, 17: 7, 11: 5})
        r, _ = self.call(v)
        self.assertEqual(r, (0x41, 40, 37))

    def test_walls_are_not_fed(self):
        v = FakeView(10, fill=FR, fill_e=8, cells=nb(up=WA))
        r, _ = self.call(v)
        self.assertEqual(r, (0x41, 40, 37))

    def test_margin_declines(self):
        r, _ = self.call(FakeView(6, fill=FR, fill_e=5))
        self.assertEqual(r, (REST, 39, 35))
        r, _ = self.call(FakeView(7, fill=FR, fill_e=5))
        self.assertEqual(r[0], 0x40)           # 7 - 2 >= 5

    def test_target_cap_declines(self):
        r, _ = self.call(FakeView(50, fill=FR, fill_e=49))
        self.assertEqual(r, (REST, 36, 32))
        r, _ = self.call(FakeView(50, fill=FR, fill_e=48))
        self.assertEqual(r[0], 0x40)

    def test_all_walls_rests(self):
        r, _ = self.call(FakeView(10, fill=WA))
        self.assertEqual(r, (REST, 36, 32))

    def test_factory_thresholds(self):
        p = rivals.make_rlock5(feed_min=12)
        self.assertEqual(p(FakeView(10, fill=FR, fill_e=5), bytearray(64))[0], REST)
        self.assertEqual(p(FakeView(12, fill=FR, fill_e=5), bytearray(64))[0], 0x40)


class Blind3Test(unittest.TestCase):
    """R-Blind3 (hypothetical, brief 2026-11-07): bites at 3 in every direction, no memory, Brawler body."""

    def test_bites_at_3_in_every_direction(self):
        for d in (UP, RIGHT, DOWN, LEFT):
            mem = bytearray(64)
            self.assertEqual(rivals.rblind3(FakeView(3, cells={NB[d]: EN}), mem), (0x30 + d, 3, 3))
            self.assertEqual(mem, bytearray(64))

    def test_several_enemies_use_sprint_priority(self):
        r = rivals.rblind3(FakeView(3, cells=nb(right=EN, left=EN)), bytearray(64))
        self.assertEqual(r[0], 0x30 + rivals._f6_bite([EN if i in (13, 11) else EM for i in range(25)]))

    def test_no_lock_next_call_has_no_enemy(self):
        mem = bytearray(64)
        rivals.rblind3(FakeView(3, cells=nb(up=EN)), mem)
        self.assertEqual(rivals.rblind3(FakeView(4), mem), (REST, 13, 12))

    def test_slow_paths_same_as_brawler(self):
        for v in (FakeView(4), FakeView(5),
                  FakeView(10, fill=FR, fill_e=20, energies={7: 9, 13: 5, 17: 7, 11: 5})):
            self.assertEqual(rivals.rblind3(v, bytearray(64)), rivals.rbrawler(v, bytearray(64)))


class BlindLock3Test(unittest.TestCase):
    """The earlier blind-lock model (first bite 9, then 3 forever), kept as hypothetical rblindlock3."""

    def call(self, view, mem=None):
        mem = bytearray(64) if mem is None else mem
        return rivals.rblindlock3(view, mem), mem

    def test_blind_lock_is_3_and_never_exits(self):
        mem = bytearray(64)
        mem[0] = 0x31
        for cells in (nb(right=EN), {}, nb(right=FR), nb(up=EN)):
            r, _ = self.call(FakeView(20, cells=cells), mem)
            self.assertEqual(r, (0x31, 3, 3))

    def test_first_bite_is_9_and_stores_the_action(self):
        r, mem = self.call(FakeView(3, cells=nb(down=EN)))
        self.assertEqual(r, (0x32, 9, 7))
        self.assertEqual(mem[0], 0x32)

    def test_no_prearm(self):
        r, mem = self.call(FakeView(4, cells={FAR[UP]: EN}))
        self.assertEqual(r, (REST, 11, 8))
        self.assertEqual(mem[0], 0)

    def test_split_and_feed_counts(self):
        self.assertEqual(self.call(FakeView(5))[0], (0x20, 19, 17))
        v = FakeView(10, fill=FR, fill_e=20, energies={7: 9, 13: 5, 17: 7, 11: 5})
        self.assertEqual(self.call(v)[0], (0x41, 32, 29))


class FatGrabTest(unittest.TestCase):
    def call(self, view, mem=None):
        mem = bytearray(64) if mem is None else mem
        return rivals.rfatgrab(view, mem), mem

    def test_front_same_as_lock5(self):
        mem = bytearray(64)
        mem[0] = lock_byte(LEFT)
        self.assertEqual(self.call(FakeView(3, cells=nb(left=EN)), mem)[0], (0x33, 5, 5))
        r, mem = self.call(FakeView(3, cells=nb(up=EN)))
        self.assertEqual((r, mem[0]), ((0x30, 10, 8), lock_byte(UP)))
        _, mem = self.call(FakeView(4, cells={FAR[RIGHT]: EN}))
        self.assertEqual(mem[0], lock_byte(RIGHT))

    def test_split_and_rest(self):
        self.assertEqual(self.call(FakeView(5))[0], (0x20, 27, 25))
        self.assertEqual(self.call(FakeView(4))[0], (REST, 19, 16))

    def test_assist_feeds_poor_friend_with_empty_neighbour(self):
        # UP friend has 3 energy and an empty square at view idx 2 (its own UP)
        v = FakeView(20, fill=FR, fill_e=20, cells={2: EM}, energies={7: 3})
        self.assertEqual(self.call(v)[0], (0x40, 48, 45))
        # LEFT friend poor with empty idx 16 (its DOWN); UP poor but boxed in -> LEFT
        v = FakeView(20, fill=FR, fill_e=20, cells={16: EM}, energies={7: 3, 11: 4})
        self.assertEqual(self.call(v)[0][0], 0x43)

    def test_assist_needs_poor_target_and_rich_donor(self):
        v = FakeView(20, fill=FR, fill_e=20, cells={2: EM}, energies={7: 5})   # target not < 5
        self.assertEqual(self.call(v)[0], (REST, 48, 44))
        v = FakeView(20, fill=FR, fill_e=20, energies={7: 3})                   # boxed in
        self.assertEqual(self.call(v)[0], (REST, 48, 44))
        v = FakeView(9, fill=FR, fill_e=20, cells={2: EM}, energies={7: 3})     # donor < 10
        self.assertEqual(self.call(v)[0], (REST, 28, 24))

    def test_capped_donor_feeds_poorest(self):
        v = FakeView(48, fill=FR, fill_e=30, energies={17: 12})
        self.assertEqual(self.call(v)[0], (0x42, 40, 36))
        v = FakeView(50, fill=FR, fill_e=49)
        self.assertEqual(self.call(v)[0][0], REST)


class RegistryTest(unittest.TestCase):
    def test_names_and_factories(self):
        for name in ('rlock5', 'rblind3', 'rblindlock3', 'rfatgrab', 'sprint', 'hunter', 'walker', 'idle'):
            self.assertTrue(callable(policies.get(name)), name)
        p = policies.get('rlock5[feed_min=12,feed_margin=3]')
        self.assertEqual(p(FakeView(12, fill=FR, fill_e=10), bytearray(64))[0], REST)   # 12 - 3 < 10
        self.assertEqual(policies.get('rlock5')(FakeView(12, fill=FR, fill_e=10), bytearray(64))[0], 0x40)
        self.assertEqual(policies.get('cells_ref:sprint'), policies.get('sprint'))
        with self.assertRaises(KeyError):
            policies.get('nosuch')


class RivalMatchTest(unittest.TestCase):
    def test_rivals_play_without_faults(self):
        pols = [policies.get(n) for n in ('rlock5', 'rblind3', 'rfatgrab', 'sprint')]
        e = E.Engine(pols, width=32, height=32, seed=4, max_ticks=300, start_mode='random',
                     start_min_dist=8)
        res = e.run()
        self.assertTrue(all(not r['faults'] for r in res))
        self.assertGreater(sum(r['births'] for r in res), 100)
        self.assertLessEqual(max(r['max_insn'] for r in res), 50)


class StaticFrontTest(unittest.TestCase):
    """Hunter-style front: cmp/je per direction in a fixed order; bite 4, 6, 8, 10; miss 8."""

    def test_brawler_order_ulrd(self):
        for k, d in enumerate((UP, LEFT, RIGHT, DOWN)):
            r = rivals.rbrawler(FakeView(3, cells={NB[d]: EN}), bytearray(64))
            self.assertEqual(r, (0x30 + d, 4 + 2 * k, 3 + 2 * k))

    def test_atompush_order_rlud(self):
        for k, d in enumerate((RIGHT, LEFT, UP, DOWN)):
            r = rivals.ratompush(FakeView(3, cells={NB[d]: EN}), bytearray(64))
            self.assertEqual(r, (0x30 + d, 4 + 2 * k, 3 + 2 * k))

    def test_first_in_order_wins_and_order_parameter(self):
        r = rivals.rbrawler(FakeView(3, cells=nb(right=EN, left=EN, down=EN)), bytearray(64))
        self.assertEqual(r[0], 0x33)
        p = policies.get('rbrawler[order=DRUL]')
        self.assertEqual(p(FakeView(3, cells=nb(up=EN, down=EN)), bytearray(64)), (0x32, 4, 3))

    def test_no_memory_writes_and_no_prearm(self):
        mem = bytearray(64)
        rivals.rbrawler(FakeView(3, cells=nb(up=EN)), mem)
        rivals.rbrawler(FakeView(4, cells={FAR[UP]: EN}), mem)
        self.assertEqual(mem, bytearray(64))

    def test_brawler_slow_paths(self):
        self.assertEqual(rivals.rbrawler(FakeView(4), bytearray(64)), (REST, 13, 12))
        self.assertEqual(rivals.rbrawler(FakeView(5), bytearray(64)), (0x20, 21, 21))
        v = FakeView(10, fill=FR, fill_e=20, energies={7: 9, 13: 5, 17: 7, 11: 5})
        self.assertEqual(rivals.rbrawler(v, bytearray(64)), (0x41, 34, 33))

    def test_atompush_slow_paths(self):
        self.assertEqual(rivals.ratompush(FakeView(5), bytearray(64)), (0x20, 21, 21))
        v = FakeView(20, fill=FR, fill_e=20, cells={2: EM}, energies={7: 3})
        self.assertEqual(rivals.ratompush(v, bytearray(64)), (0x40, 42, 41))
        v = FakeView(48, fill=FR, fill_e=30, energies={17: 12})
        self.assertEqual(rivals.ratompush(v, bytearray(64)), (0x42, 34, 32))

    def test_lock_variants_still_registered(self):
        self.assertEqual(policies.get('rlock5')(FakeView(3, cells=nb(up=EN)), bytearray(64)), (0x30, 10, 8))
        self.assertEqual(policies.get('rfatgrab')(FakeView(3, cells=nb(up=EN)), bytearray(64)), (0x30, 10, 8))


class PumpTest(unittest.TestCase):
    """rpump: Brawler front (U,L,R,D), interior feeds its richest friend neighbour (uphill) up to 48;
    capped (> 48) neighbours are skipped; cells that see an enemy within the 5x5 view but not adjacent
    hold their energy (rest)."""

    def call(self, v):
        return rivals.rpump(v, bytearray(64))

    def test_front_same_as_brawler(self):
        self.assertEqual(self.call(FakeView(3, cells=nb(left=EN))), (0x33, 6, 5))

    def test_split_and_low_rest(self):
        self.assertEqual(self.call(FakeView(5)), (0x20, 21, 21))
        self.assertEqual(self.call(FakeView(4)), (REST, 13, 12))

    def test_near_front_holds(self):
        v = FakeView(30, fill=FR, fill_e=20, cells={0: EN})
        self.assertEqual(self.call(v), (REST, 26, 24))

    def test_interior_feeds_richest_uphill(self):
        v = FakeView(20, fill=FR, fill_e=20, energies={7: 25, 13: 40, 17: 40, 11: 10})
        self.assertEqual(self.call(v), (0x41, 43, 42))       # ties -> first in U, R, D, L

    def test_target_cap_and_no_friend(self):
        v = FakeView(20, fill=FR, fill_e=49)
        self.assertEqual(self.call(v), (REST, 42, 40))
        v = FakeView(20, fill=FR, fill_e=49, energies={11: 48})
        self.assertEqual(self.call(v), (0x43, 43, 42))        # capped neighbours skipped
        v = FakeView(20, fill=WA)
        self.assertEqual(self.call(v), (REST, 42, 40))

    def test_pump_min(self):
        v = FakeView(15, fill=FR, fill_e=20)
        self.assertEqual(self.call(v), (REST, 28, 26))
        p = policies.get('rpump[pump_min=10]')
        self.assertEqual(p(v, bytearray(64))[0], 0x40)


if __name__ == '__main__':
    unittest.main()
