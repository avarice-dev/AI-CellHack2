"""Tests of Misfortune (planned): a 2-instruction chain bite read from a slot table indexed by the cell's own energy.

Spec: briefs/misfortune-spec-2026-11-13.md.  Memory: [0] bearing, [1] steps, [4..7] position (Bane v2.2), [8] = e0 of
the last arming, slot(e) = byte 13 + e (byte 63 = slot 50), bytes 2-3 and 9-12 unused.
- Entry `or al, [base + 13 + rsi]` / `jnz EXIT`: a non-zero slot is played, 2 instructions (1 without taken jumps).
- Slow-path prefix: zero bytes 9 + [8] .. 24 + [8]; then Bane v2.2's paths, at Bane v2.3a's count - 1.
- Arming (scan bite toward d at energy e0): byte 8 = e0; EAT + d on the slots of e0's parity in e0 - 4 .. e0 + 10;
  exact=1 only up to e0 + 2k, k = (te + 1) // 2 - 1 (k = 0: none).  Slot 50: cap A arms it when e0 >= 40 and slot 48
  or 49 is armed; B and N never.  First bite 16 (exact 0) / 19 (exact 1), cap A + 3.
- Boxed cap rules ahead of Bane's boxed rules.  A: EAT the first edge friend at 47+ with an empty edge and no enemy
  on its edges.  B: EAT the first edge friend at 48+ with an enemy on its edges, else FEED the first edge friend at
  47+ with an empty edge and no enemy on its edges (my energy >= 6).  N: none.  A cap-rule action counts
  MISFORTUNE_PULL_N, more than any path the pulled cell can be on.

MisfortuneRefTest: unit tests of sim/cells_ref.make_misfortune (one module, no I/O); view and memory are faked.
Expected values come from the spec above and from Bane v2.3a (cells_ref.make_bane3), not from Misfortune itself.
MisfortuneEngineTest: integration tests on the real engine (sim/engine.py) with our own reference cells, small boards.
"""

import itertools
import random
import unittest

import cells_ref
import engine as E
from .test_bane2 import View, mem, UP, RIGHT, DOWN, LEFT, EM, FR, EN, WA
from .helpers import board, script

EAT, FEED, SPLIT_K = 0x30, 0x40, 0x20
SLOT0 = 13
IDX = (7, 13, 17, 11)
RING = {UP: (2, 6, 8), RIGHT: (8, 14, 18), DOWN: (16, 18, 22), LEFT: (6, 10, 16)}
VARIANTS = [(cap, exact) for cap in 'ABN' for exact in (0, 1)]
BITE_N = {(0, 'B'): 16, (0, 'N'): 16, (0, 'A'): 19, (1, 'B'): 19, (1, 'N'): 19, (1, 'A'): 22}


def slots(m):
    """{energy: action} of the non-zero slots 0..50."""
    return {e: m[SLOT0 + e] for e in range(51) if m[SLOT0 + e]}


def armed_view(e0, te=20, d=RIGHT):
    adj = [EM, EM, EM, EM]
    adj[d] = EN
    v = View(e0, tuple(adj))
    v.energies[IDX[d]] = te
    return v


def expected_slots(e0, d, te, cap, exact):
    """The spec's armed slots, written out independently of cells_ref."""
    top = e0 + 10
    if exact:
        k = (te + 1) // 2 - 1
        top = min(top, e0 + 2 * k) if k > 0 else -99
    out = {s: EAT + d for s in range(max(0, e0 - 4), min(50, top) + 1) if (s - e0) % 2 == 0}
    out.pop(50, None)
    if cap == 'A' and e0 >= 40 and (48 in out or 49 in out):
        out[50] = EAT + d
    return out


def armed_memory(e0, cap, d=RIGHT):
    """Memory after an arming at e0 (full window), with state bytes set."""
    m = mem(bear=3, steps=7, pos=(30, 31))
    cells_ref.make_misfortune(cap=cap, exact=0)(armed_view(e0, te=50, d=d), m)
    return m


class Spy(bytearray):
    """Memory that logs every index read and written."""
    def __init__(self, src):
        bytearray.__init__(self, src)
        self.reads, self.writes = [], []

    def _idx(self, k):
        if isinstance(k, slice):
            return list(range(*k.indices(1 << 20)))[:max(0, (k.stop or 0) - (k.start or 0))]
        return [k]

    def __getitem__(self, k):
        self.reads += self._idx(k)
        return bytearray.__getitem__(self, k)

    def __setitem__(self, k, v):
        self.writes += self._idx(k)
        return bytearray.__setitem__(self, k, v)


class MisfortuneRefTest(unittest.TestCase):
    def test_armed_bite_is_two_instructions_and_writes_nothing(self):
        for cap, exact in VARIANTS:
            p = cells_ref.make_misfortune(cap=cap, exact=exact)
            for e in range(1, 51):
                m = mem(bear=RIGHT, steps=0, pos=(30, 31))
                m[SLOT0 + e] = EAT + LEFT
                before = bytes(m)
                self.assertEqual(p(View(e, (EM, EM, EM, EM)), m), (EAT + LEFT, 2, 1))   # blind: no enemy in view
                self.assertEqual(bytes(m), before)

    def test_first_bite_counts(self):
        for cap, exact in VARIANTS:
            p = cells_ref.make_misfortune(cap=cap, exact=exact)
            n = BITE_N[(exact, cap)]
            self.assertEqual(p(armed_view(20), mem()), (EAT + RIGHT, n, n - 1), (cap, exact))

    def test_armed_slots_window_parity_and_slot50(self):
        for cap, exact in VARIANTS:
            p = cells_ref.make_misfortune(cap=cap, exact=exact)
            for e0 in range(1, 51):
                for d in range(4):
                    for te in (1, 2, 5, 6, 9, 20, 50):
                        m = mem()
                        p(armed_view(e0, te=te, d=d), m)
                        got = slots(m)
                        self.assertEqual(got, expected_slots(e0, d, te, cap, exact), (cap, exact, e0, d, te))
                        self.assertEqual(m[8], e0)
                        for s in got:
                            self.assertTrue(e0 - 4 <= s <= e0 + 10, (cap, exact, e0, s))
                            self.assertTrue((s - e0) % 2 == 0 or (s == 50 and cap == 'A'))
                        if cap != 'A':
                            self.assertEqual(m[63], 0)

    def test_prefix_clean(self):
        """Any stored e0 0-50 after an arming there (any cap) and any current energy with an empty slot:
        bytes 13-63 end zero; the prefix alone leaves bytes 0-8 unchanged."""
        for cap in 'ABN':
            for e0 in range(0, 51):
                m = armed_memory(e0, cap) if e0 else mem(bear=3, steps=7, pos=(30, 31))
                state = bytes(m[0:9])
                cells_ref.misfortune_prefix(m)
                self.assertEqual(bytes(m[13:64]), bytes(51), (cap, e0))
                self.assertEqual(bytes(m[0:9]), state, (cap, e0))
                p = cells_ref.make_misfortune(cap=cap, exact=1)
                for e in range(1, 51):
                    m = armed_memory(e0, cap) if e0 else mem()
                    if m[SLOT0 + e]:
                        continue                       # armed: a chain bite, not a slow path
                    p(View(e, (EM, FR, WA, EM)), m)
                    self.assertEqual(bytes(m[13:64]), bytes(51), (cap, e0, e))

    def test_prefix_zeroes_exactly_the_16_byte_window(self):
        """The prefix is one 16-byte store at byte 9 + [8] (clipped at 63): exactly those bytes become zero."""
        for b in range(0, 51):
            m = bytearray([0xFF] * 64)
            m[8] = b
            cells_ref.misfortune_prefix(m)
            want = [0 if 9 + b <= k <= 24 + b else (b if k == 8 else 0xFF) for k in range(64)]
            self.assertEqual(list(m), want, b)

    def test_no_access_out_of_range(self):
        """No store below byte 0 or past byte 63; the entry read stays in 13..63, for energies 0-50."""
        for cap, exact in VARIANTS:
            p = cells_ref.make_misfortune(cap=cap, exact=exact)
            for e in range(0, 51):
                for view in (armed_view(e) if e else View(0, (EM, EM, EM, EM)), View(e, (FR, FR, FR, FR))):
                    m = Spy(mem())
                    m[8] = 50
                    m.reads, m.writes = [], []
                    p(view, m)
                    self.assertEqual(len(m), 64)
                    self.assertTrue(all(0 <= k < 64 for k in m.writes), (cap, exact, e))
                    self.assertTrue(all(0 <= k < 64 for k in m.reads), (cap, exact, e))
                    self.assertEqual(m.reads[0], SLOT0 + e)

    def test_every_split_leaves_child_clean(self):
        """The engine copies the parent's memory after its call: on every split path bytes 13-63 are zero."""
        rng = random.Random(3)
        seen = 0
        for cap, exact in VARIANTS:
            p = cells_ref.make_misfortune(cap=cap, exact=exact)
            for _ in range(4000):
                e0 = rng.randint(1, 50)
                m = armed_memory(e0, cap)
                e = rng.randint(5, 50)
                if m[SLOT0 + e]:
                    continue
                adj = tuple(rng.choice((EM, EM, FR, WA)) for _ in range(4))
                v = View(e, adj, far=rng.sample((2, 6, 8, 10, 14, 16, 18, 22), rng.randint(0, 2)),
                         tick=rng.choice((5, 100, 2990)))
                m[0], m[1] = rng.randint(0, 3), rng.randint(0, 3)
                if rng.random() < 0.5:
                    m[4:8] = (30 | 31 << 16).to_bytes(4, 'little')
                a = p(v, m)[0]
                if a & 0xF0 == SPLIT_K:
                    seen += 1
                    self.assertEqual(bytes(m[13:64]), bytes(51), (cap, exact, e0, e))
        self.assertGreater(seen, 1000)

    def test_slow_paths_are_bane23a_minus_one(self):
        """No slot armed, no enemy beside the cell, not boxed (or cap N): Bane v2.3a's action and memory bytes 0-7,
        its counts - 1 (the scan keeps Bane v2.2's `or al` instead of v2.3a's mov ax / test al)."""
        rng = random.Random(7)
        for cap in 'ABN':
            p, ref = cells_ref.make_misfortune(cap=cap, exact=1), cells_ref.make_bane3()
            for _ in range(3000):
                adj = tuple(rng.choice((EM, FR, FR, WA)) for _ in range(4))
                boxed = EM not in adj
                if boxed and cap != 'N':
                    continue
                v = View(rng.randint(1, 50), adj, far=rng.sample((2, 6, 8, 10, 14, 16, 18, 22), rng.randint(0, 2)),
                         tick=rng.choice((5, 100, 2990)))
                for i in range(25):
                    if v.cells[i] in (FR, EN) and i != 12:
                        v.energies[i] = rng.randint(1, 50)
                m1 = mem(bear=rng.randint(0, 3), steps=rng.randint(0, 3), pos=rng.choice(((30, 31), (1, 2))))
                m2 = bytearray(m1)
                a1, n1, t1 = p(v, m1)
                a2, n2, t2 = ref(v, m2)
                self.assertEqual((a1, n1, t1), (a2, n2 - 1, t2 - 1), (cap, adj, v.energy))
                self.assertEqual(bytes(m1[0:8]), bytes(m2[0:8]))

    def _boxed(self, e, friend_d, fe, enemy_edge, empty_edge, puller_boxed=True):
        """Puller at energy e; edge friend at friend_d with energy fe; that friend's three other edges hold an
        enemy and / or an empty square as asked, else friends.  The other three edge squares are friends at 20 with
        all-friend edges (or, puller_boxed False, the square opposite friend_d is empty)."""
        adj = [FR, FR, FR, FR]
        if not puller_boxed:
            adj[(friend_d + 2) % 4] = EM
        v = View(e, tuple(adj))
        for d in range(4):
            v.energies[IDX[d]] = 20 if adj[d] == FR else 0
            for i in RING[d]:
                v.cells[i] = FR
                v.energies[i] = 20
        v.energies[IDX[friend_d]] = fe
        ring = list(RING[friend_d])
        if enemy_edge:
            v.cells[ring.pop(0)] = EN
        if empty_edge:
            v.cells[ring.pop()] = EM
        return v

    def test_cap_rule_truth_table(self):
        """Friend energy 46-50 x enemy on its edge x empty edge x puller boxed, each friend direction, caps A B N."""
        ref = cells_ref.make_bane3()
        for cap in 'ABN':
            p = cells_ref.make_misfortune(cap=cap, exact=1)
            for fe, en_e, em_e, boxed, d in itertools.product(range(46, 51), (0, 1), (0, 1), (0, 1), range(4)):
                for e in (4, 20):
                    v = self._boxed(e, d, fe, en_e, em_e, boxed)
                    want = None
                    if boxed and cap == 'A' and fe >= 47 and em_e and not en_e:
                        want = EAT + d
                    if boxed and cap == 'B':
                        if fe >= 48 and en_e:
                            want = EAT + d
                        elif fe >= 47 and em_e and not en_e and e >= 6:
                            want = FEED + d
                    a, n, _ = p(v, mem())
                    key = (cap, fe, en_e, em_e, boxed, d, e)
                    if want is not None:
                        self.assertEqual((a, n), (want, cells_ref.MISFORTUNE_PULL_N), key)
                    else:
                        self.assertEqual(a, ref(v, mem())[0], key)
                        self.assertNotEqual(n, cells_ref.MISFORTUNE_PULL_N, key)

    def test_interior_at_50_never_eats(self):
        """All-friend interior: every edge friend at 50 with all-friend edges, me at 50: no EAT under any cap."""
        for cap in 'ABN':
            p = cells_ref.make_misfortune(cap=cap, exact=1)
            v = View(50, (FR, FR, FR, FR))
            for i in range(25):
                if i != 12:
                    v.cells[i] = FR
                    v.energies[i] = 50
            a = p(v, mem())[0]
            self.assertNotEqual(a & 0xF0, EAT, cap)

    def test_pull_count_exceeds_every_path_of_the_pulled_cell(self):
        """A pulled friend has an empty edge (A, B's feed) or an enemy edge (B's eat), so it is never boxed: every
        non-boxed path of every variant is below MISFORTUNE_PULL_N, so a pull runs after it and never stuns it."""
        rng = random.Random(11)
        worst = 0
        for cap, exact in VARIANTS:
            p = cells_ref.make_misfortune(cap=cap, exact=exact)
            for _ in range(6000):
                adj = tuple(rng.choice((EM, FR, FR, WA, EN)) for _ in range(4))
                if EM not in adj and EN not in adj:
                    continue
                v = View(rng.randint(1, 50), adj, far=rng.sample((2, 6, 8, 10, 14, 16, 18, 22), rng.randint(0, 3)),
                         tick=rng.choice((0, 5, 100, 2990)), x=rng.randint(0, 63), y=rng.randint(0, 63))
                for i in range(25):
                    if v.cells[i] in (FR, EN) and i != 12:
                        v.energies[i] = rng.randint(1, 50)
                m = armed_memory(rng.randint(1, 50), cap) if rng.random() < 0.3 else \
                    mem(bear=rng.randint(0, 3), steps=rng.randint(0, 8), pos=rng.choice(((v.x, v.y), (1, 2))))
                worst = max(worst, p(v, m)[1])
        self.assertLess(worst, cells_ref.MISFORTUNE_PULL_N)
        self.assertGreater(worst, 40)                  # the sweep reached the long settled paths

    def test_bad_flags(self):
        with self.assertRaises(ValueError):
            cells_ref.make_misfortune(cap='X')
        with self.assertRaises(ValueError):
            cells_ref.make_misfortune(exact=2)


def recording(policy, log):
    def pol(view, mem):
        r = policy(view, mem)
        log.append((view.tick, view.x, view.y, view.energy, r[0], r[1]))
        return r
    return pol


class MisfortuneEngineTest(unittest.TestCase):
    def test_bitten_on_its_arming_tick_is_armed_at_two(self):
        """Tick 0: the enemy bites first (count 1), so Misfortune is stunned on its arming call; the writes persist
        (engine default), so on tick 1 at energy 18 it bites from slot 18 in 2 instructions."""
        log = []
        en = script({(0, 2, 2): (EAT + LEFT, 1)}, default=(E.ACT_NOP, 1))
        eng = board([recording(cells_ref.make_misfortune(cap='B', exact=1), log), en], w=5, h=5)
        a = eng.add_cell(1, 2, 0, 20)
        b = eng.add_cell(2, 2, 1, 20)
        eng.step()
        self.assertEqual((eng.c_en[a], eng.c_en[b]), (18, 22))
        self.assertEqual(log[-1][5], 19)
        eng.step()
        self.assertEqual(log[-1][3:], (18, EAT + RIGHT, 2))
        self.assertEqual((eng.c_en[a], eng.c_en[b]), (20, 20))

    def _run_on_target(self, cap, e0, te, ticks):
        """Misfortune at (1, 2) with energy e0 beside an idle enemy (NOP) at (2, 2) with energy te (7 x 5 board)."""
        log = []
        eng = board([recording(cells_ref.make_misfortune(cap=cap, exact=1), log), script({}), script({})], w=7, h=5)
        a = eng.add_cell(1, 2, 0, e0)
        b = eng.add_cell(2, 2, 1, te)
        eng.add_cell(6, 0, 2, 10)                      # a third colony far away keeps the match running
        for _ in range(ticks):
            eng.step()
        return eng, log, a, b

    def test_run_end_after_kill_odd_last_bite(self):
        """te 5: bites take 2, 2, 1; the run (slots 22, 24) ends on the kill tick; energy 25 (odd) -> slow path."""
        eng, log, a, b = self._run_on_target('B', 20, 5, 4)
        self.assertEqual([(r[3], r[5]) for r in log[:3]], [(20, 19), (22, 2), (24, 2)])
        self.assertFalse(eng.c_alive[b] if b < len(eng.c_alive) else False)
        self.assertEqual(log[3][3], 25)
        self.assertNotEqual(log[3][5], 2)

    def test_run_end_after_kill_even(self):
        """te 6: bites take 2, 2, 2; after the kill at 26 the slot is empty (top armed slot 24): slow path."""
        eng, log, a, b = self._run_on_target('B', 20, 6, 4)
        self.assertEqual([(r[3], r[5]) for r in log[:3]], [(20, 19), (22, 2), (24, 2)])
        self.assertEqual(log[3][3], 26)
        self.assertNotEqual(log[3][5], 2)

    def test_cap_49_to_50(self):
        """e0 49 beside a 40-energy enemy: 49 + 2 is capped to 50 at Tidy.  Cap A: slot 50 armed (2 again);
        cap B: slot 50 empty, a slow path (rescan at the arming count)."""
        _, log, _, _ = self._run_on_target('A', 49, 40, 2)
        self.assertEqual([(r[3], r[5]) for r in log], [(49, 22), (50, 2)])
        _, log, _, _ = self._run_on_target('B', 49, 40, 2)
        self.assertEqual([(r[3], r[5]) for r in log], [(49, 19), (50, 19)])

    def _game(self, subject, seed, ticks=400):
        pols = [subject, cells_ref.make_bane2(), cells_ref.make_conviction(), cells_ref.make_penalty()]
        return E.Engine(pols, seed=seed, max_ticks=ticks, start_mode='random')

    def _contact(self, eng, colony):
        for i in eng.live:
            if eng.c_col[i] == colony and eng.c_alive[i]:
                for o in eng.dirs:
                    g = eng.grid[eng.c_pos[i] + o]
                    if g >= 0 and eng.c_alive[g] and eng.c_col[g] != colony:
                        return True
        return False

    def test_cap_n_matches_bane23a_until_first_contact(self):
        """Seat 0: Misfortune cap N, and Bane v2.3a with its counts - 1 (same turn order): identical colony cells
        and energy every tick until a seat-0 cell first has an enemy on an edge."""
        ref = cells_ref.make_bane3()

        def shifted(view, mem):
            a, n, t = ref(view, mem)
            return a, n - 1, t - 1
        for seed in (1, 2):
            e1 = self._game(cells_ref.make_misfortune(cap='N', exact=1), seed)
            e2 = self._game(shifted, seed)
            ticks = 0
            while not self._contact(e1, 0):
                self.assertFalse(self._contact(e2, 0))
                e1.step()
                e2.step()
                ticks += 1
                self.assertEqual((e1.pop, e1.energy), (e2.pop, e2.energy), (seed, e1.tick))
            self.assertGreater(ticks, 10, seed)


if __name__ == '__main__':
    unittest.main()
