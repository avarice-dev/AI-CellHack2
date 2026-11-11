"""Tests of Bane v2 (designs.md 11.3): Bane plus a dispersal opening.

Bane2RefTest: unit test of sim/cells_ref.make_bane2; the view and the memory are faked.  Expected results are written
from the spec, not from the policy.
Bane2GenTest: unit test of cells/gen_bane2.py: the committed asm is the generator's output, the bite and gate-1 lines
are Bane's verbatim, and it has no paste-breaking directives.
Bane2SoloTest: integration test, real engine + the Bane v2 policy alone on the board (nothing faked): the opening
must beat the real opening of the ladder leader measured in data pull 7 (cells at t60 and t100).
"""

import os
import unittest

from .helpers import E
import cells_ref

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
IDX = (7, 13, 17, 11)                    # view index of the neighbour in direction d
EM, FR, EN, WA = 0, 1, 2, 3
MOVE, SPLIT, REST = 0x10, 0x20, 0x01
CELLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cells')


class View(object):
    def __init__(self, energy, adj=(EM, EM, EM, EM), far=(), tick=100, x=30, y=31, friends=()):
        self.cells = [EM] * 25
        self.cells[12] = FR
        self.energies = [0] * 25
        self.energies[12] = energy
        for i, t in zip(IDX, adj):
            self.cells[i] = t
            self.energies[i] = 20 if t in (FR, EN) else 0
        for i in far:
            self.cells[i] = EN
            self.energies[i] = 9
        for i in friends:
            self.cells[i] = FR
            self.energies[i] = 9
        self.energy, self.tick, self.x, self.y, self.w, self.h = energy, tick, x, y, 64, 64


def mem(bear=0, steps=0, pos=None):
    m = bytearray(64)
    m[0], m[1] = bear, steps
    if pos is not None:
        m[4:8] = (pos[0] | pos[1] << 16).to_bytes(4, 'little')
    return m


def pos_of(m):
    v = int.from_bytes(m[4:8], 'little')
    return v & 0xFFFF, v >> 16


class Bane2RefTest(unittest.TestCase):
    def setUp(self):
        self.p = cells_ref.make_bane2()
        self.KL, self.KS, self.TE = cells_ref.BANE2_K_LONG, cells_ref.BANE2_K_SHORT, cells_ref.BANE2_T_EARLY

    def test_walker_moves_along_its_bearing(self):
        for d in range(4):
            m = mem(bear=d, steps=5, pos=(10, 10))          # emitted elsewhere: this cell is the child
            act = self.p(View(2), m)[0]
            self.assertEqual(act, MOVE + d)
            self.assertEqual(m[1], 4)

    def test_walker_with_enough_energy_still_walks(self):
        m = mem(bear=RIGHT, steps=3, pos=(10, 10))
        self.assertEqual(self.p(View(5), m)[0], MOVE + RIGHT)

    def test_blocked_walker_settles_and_rests(self):
        for block in (FR, WA):
            adj = [EM] * 4
            adj[UP] = block
            m = mem(bear=UP, steps=5, pos=(10, 10))
            self.assertEqual(self.p(View(2, adj), m)[0], REST)
            self.assertEqual(m[1], 0)

    def test_emitter_does_not_walk(self):
        m = mem(bear=UP, steps=8, pos=(30, 31))             # this cell emitted from its own square
        self.assertEqual(self.p(View(3), m)[0], REST)
        self.assertEqual(m[1], 8)

    def test_first_emission_goes_forward_and_long(self):
        for d in range(4):
            m = mem(bear=d, steps=0, pos=(10, 10))
            self.assertEqual(self.p(View(5), m)[0], SPLIT + d)
            self.assertEqual((m[0], m[1], pos_of(m)), (d, self.KL, (30, 31)))

    def test_first_emission_turns_clockwise_and_short_when_forward_is_blocked(self):
        adj = [EM] * 4
        adj[UP] = FR
        m = mem(bear=UP, steps=0, pos=(10, 10))
        self.assertEqual(self.p(View(5, adj), m)[0], SPLIT + RIGHT)
        self.assertEqual((m[0], m[1]), (RIGHT, self.KS))

    def test_later_emissions_rotate_clockwise_and_are_short(self):
        m = mem(bear=UP, steps=self.KL, pos=(30, 31))
        seen = []
        for _ in range(5):
            seen.append(self.p(View(5), m)[0] - SPLIT)
            self.assertEqual(m[1], self.KS)
        self.assertEqual(seen, [RIGHT, DOWN, LEFT, UP, RIGHT])

    def test_rotation_skips_occupied_squares(self):
        adj = [EM, FR, WA, EM]                              # RIGHT friend, DOWN wall
        m = mem(bear=UP, steps=0, pos=(30, 31))
        self.assertEqual(self.p(View(7, adj), m)[0], SPLIT + LEFT)
        adj = [EM, FR, FR, FR]                              # only the last emission direction is free
        m = mem(bear=UP, steps=0, pos=(30, 31))
        self.assertEqual(self.p(View(7, adj), m)[0], SPLIT + UP)

    def test_early_emissions_are_all_long_when_t_early_is_set(self):
        p = cells_ref.make_bane2(t_early=12)
        m = mem(bear=UP, steps=self.KL, pos=(30, 31))
        self.assertEqual(p(View(5, tick=11), m)[0], SPLIT + RIGHT)
        self.assertEqual(m[1], self.KL)
        m = mem(bear=UP, steps=self.KL, pos=(30, 31))
        p(View(5, tick=12), m)
        self.assertEqual(m[1], self.KS)
        self.assertEqual(self.TE, 0)                        # the shipped setting: off

    def test_start_cell_first_call(self):
        m = bytearray(64)
        self.assertEqual(self.p(View(10, tick=0), m)[0], SPLIT + UP)
        self.assertEqual((m[0], m[1], pos_of(m)), (UP, self.KL, (30, 31)))

    def test_thin_settled_cell_rests(self):
        m = mem(bear=LEFT, steps=0, pos=(10, 10))
        self.assertEqual(self.p(View(4), m)[0], REST)
        self.assertEqual(bytes(m), bytes(mem(bear=LEFT, steps=0, pos=(10, 10))))

    def test_enemy_in_view_stops_a_walker_and_holds(self):
        for e, want in ((2, REST), (5, REST), (15, REST)):
            m = mem(bear=UP, steps=5, pos=(10, 10))
            self.assertEqual(self.p(View(e, far=(0,)), m)[0], want)
            self.assertEqual(m[1], 0)

    def test_enemy_in_view_late_tick_splits_like_bane(self):
        m = mem(bear=UP, steps=5, pos=(10, 10))
        v = View(6, far=(0,), tick=2980)
        self.assertEqual(self.p(v, m)[0], cells_ref.bane(v, bytearray(64))[0])

    def test_stored_bite(self):
        m = mem(bear=RIGHT, steps=4, pos=(10, 10))
        v = View(20, (EM, EN, EM, EM))
        self.assertEqual(self.p(v, m)[:2], (0x30 + RIGHT, 16))          # first bite: scan, then store
        self.assertEqual((m[2], m[3]), (13 + 8, 0x30 + RIGHT))
        self.assertEqual(self.p(v, m), (0x30 + RIGHT, 4, 3))            # same enemy next tick: 4 instructions
        v2 = View(20, (EN, EN, EM, EM))                                 # a second enemy: keep biting the stored one
        self.assertEqual(self.p(v2, m)[:2], (0x30 + RIGHT, 4))
        gone = View(20, (EM, FR, EM, EM))                               # a friend took the square: never bite it
        act, n = self.p(gone, m)[:2]
        self.assertEqual(act & 0xF0, SPLIT)
        self.assertEqual(n, 16)
        other = View(20, (EN, EM, EM, EM))                              # enemy elsewhere: scan again, store anew
        self.assertEqual(self.p(other, m)[:2], (0x30 + UP, 16))
        self.assertEqual((m[2], m[3]), (7 + 8, 0x30 + UP))

    def test_gate1_and_boxed_paths_are_banes_plus_five(self):
        cases = [View(16), View(40),                          # gate 1, e >= 16
                 View(12, far=(6,)),                          # refill
                 View(3, (FR, FR, FR, WA)), View(30, (FR, FR, FR, FR)),   # boxed
                 View(8, (FR, FR, FR, FR), friends=(6, 8, 16, 18))]
        for v in cases:
            m = mem(bear=RIGHT, steps=4, pos=(10, 10))
            a, n, t = cells_ref.bane(v, bytearray(64))
            self.assertEqual(self.p(v, m), (a, n + 5, t + 5))
            self.assertEqual(bytes(m), bytes(mem(bear=RIGHT, steps=4, pos=(10, 10))))

    def test_instruction_counts_of_the_new_paths(self):
        # traced by hand from cells/gen_bane2.py's asm (every executed instruction incl. taken jumps and ret)
        self.assertEqual(self.p(View(2), mem(UP, 5, (10, 10)))[1:], (39, 39))            # walker move
        self.assertEqual(self.p(View(5), mem(UP, 0, (10, 10)))[1:], (43, 41))            # first emission, long
        self.assertEqual(self.p(View(4), mem(UP, 0, (10, 10)))[1:], (33, 31))            # thin settled cell rests
        self.assertEqual(self.p(View(5), mem(UP, 8, (30, 31)))[1:], (50, 46))            # emitter, next square, short
        self.assertEqual(self.p(View(2, far=(0,)), mem(UP, 5, (10, 10)))[1:], (31, 29))  # enemy in view, e < 5
        self.assertEqual(self.p(View(9, far=(0,)), mem(UP, 5, (10, 10)))[1:], (33, 32))  # hold


class Bane2GenTest(unittest.TestCase):
    def test_committed_asm_is_the_generator_output(self):
        import sys
        sys.path.insert(0, CELLS_DIR)
        import gen_bane2
        with open(os.path.join(CELLS_DIR, 'bane2.asm'), newline='') as f:
            self.assertEqual(f.read(), gen_bane2.generate())

    def test_gate1_lines_are_banes(self):
        def gate(name):
            txt = open(os.path.join(CELLS_DIR, name)).read()
            a = txt.index('slow:')
            return txt[txt.index('\n', a):txt.index('\tjz\t\tboxed')]
        self.assertEqual(gate('bane2.asm'), gate('bane.asm'))

    def test_paste_rules(self):
        src = open(os.path.join(CELLS_DIR, 'bane2.asm')).read()
        code = '\n'.join(l.split(';')[0] for l in src.splitlines())
        for word in ('org ', 'bits ', 'section', '%include', 'rdx'):
            self.assertNotIn(word, code)


class Bane2SoloTest(unittest.TestCase):
    """Real engine, one colony.  Thresholds: the ladder leader's real mean in data pull 7 (four-colony games):
    907 cells at t60, 2028 at t100."""

    def run_solo(self, start, ticks):
        eng = E.Engine([cells_ref.bane2], seed=3, max_ticks=ticks, start_mode='fixed', start_positions=[start])
        pops = {}
        while eng.step():
            pops[eng.tick] = eng.pop[0]
        pops[eng.tick] = eng.pop[0]
        return pops, eng

    def test_opening_beats_the_leader_from_the_centre(self):
        pops, eng = self.run_solo((30, 31), 100)
        self.assertGreaterEqual(pops[60], 907)
        self.assertGreaterEqual(pops[100], 2028)

    def test_opening_beats_the_leader_from_a_corner_region(self):
        pops, eng = self.run_solo((8, 9), 100)
        self.assertGreaterEqual(pops[60], 907)
        self.assertGreaterEqual(pops[100], 2028)

    def test_board_fills(self):
        pops, eng = self.run_solo((30, 31), 300)
        self.assertGreaterEqual(pops[300], 4000)


if __name__ == '__main__':
    unittest.main()
