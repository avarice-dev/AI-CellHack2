"""Tests of Bane v2.3a: Bane v2.2 with a cheaper first bite and no behaviour change.

Spec: the first bite (no stored bite, an enemy beside the cell) costs 12 instructions, not 16. One 16-bit table load
gives the eat action and the stored-bite square together, and one 16-bit store writes both. The stored-bite bytes swap
places: [2] = the action, [3] = view index + 8 of the square. Every action, every other instruction count and every
other memory byte is Bane v2.2's.

Bane3RefTest: unit test of sim/cells_ref.make_bane3; the view and the memory are faked. Expected values come from
the spec above and from Bane v2.2 (cells_ref.bane2), not from the new policy.
Bane3GenTest: unit test of cells/gen_bane3.py: the committed asm is the generator's output, the gate-1 lines are
Bane's verbatim, lock2_tbl holds action | square << 8 for every bite mask, and the file is pasteable.
"""

import itertools
import os
import sys
import unittest

import cells_ref
from .test_bane2 import View, mem, UP, RIGHT, EM, FR, EN, WA, SPLIT, CELLS_DIR

EAT = 0x30


def swap(m):
    """The same memory in the other stored-bite layout ([2] and [3] exchanged)."""
    m = bytearray(m)
    m[2], m[3] = m[3], m[2]
    return m


class Bane3RefTest(unittest.TestCase):
    def setUp(self):
        self.p = cells_ref.make_bane3()

    def test_stored_bite(self):
        m = mem(bear=RIGHT, steps=4, pos=(10, 10))
        v = View(20, (EM, EN, EM, EM))
        self.assertEqual(self.p(v, m), (EAT + RIGHT, 12, 11))          # first bite: scan, store, 12
        self.assertEqual((m[2], m[3]), (EAT + RIGHT, 13 + 8))         # [2] action, [3] square
        self.assertEqual(self.p(v, m), (EAT + RIGHT, 4, 3))            # same enemy next tick: 4 instructions
        v2 = View(20, (EN, EN, EM, EM))                                # a second enemy: keep biting the stored one
        self.assertEqual(self.p(v2, m)[:2], (EAT + RIGHT, 4))
        gone = View(20, (EM, FR, EM, EM))                              # a friend took the square: never bite it
        act, n = self.p(gone, m)[:2]
        self.assertEqual(act & 0xF0, SPLIT)
        self.assertEqual(n, 16)                                        # Bane v2.2's split path, unchanged
        self.assertEqual((m[2], m[3]), (EAT + RIGHT, 13 + 8))         # a miss keeps the old stored bite
        other = View(20, (EN, EM, EM, EM))                             # enemy elsewhere: scan again, store anew
        self.assertEqual(self.p(other, m)[:2], (EAT + UP, 12))
        self.assertEqual((m[2], m[3]), (EAT + UP, 7 + 8))

    def test_same_as_bane2_on_every_path(self):
        """Every adjacent-type pattern x energies x far enemies x stored bites x memory states: Bane v2.2's action and
        memory (layout swapped), Bane v2.2's counts, except the first bite: 12 / 11 for v2.2's 16 / 15."""
        locks = ((0, 0), (15, EAT + 0), (21, EAT + 1), (25, EAT + 2), (19, EAT + 3), (0, EAT + 1), (21, EAT + 3))
        mems = ((0, 0, False), (0, 5, False), (3, 2, True), (1, 0, False), (2, 8, True))
        es, fars, ticks = (0, 4, 5, 11, 12, 16, 50), ((), (6,), (0,), (2, 22)), (0, 2980)
        adj = list(itertools.product((EM, FR, EN, WA), repeat=4))
        cases = [(t, es[i % 7], fars[i % 4], ticks[i % 2], lk, mems[i % 5])        # every stored bite x pattern
                 for i, (t, lk) in enumerate(itertools.product(adj, locks))]
        cases += [(t, e, f, ticks[i % 2], locks[i % 7], ms)                          # every energy x far x memory
                  for i, (t, e, f, ms) in enumerate(itertools.product(adj, es, fars, mems))]
        first = hits = 0
        for types, e, far, tick, lock, ms in cases:
            case = (types, e, far, tick, lock, ms)
            v = View(e, types, far=far, tick=tick)
            m2 = mem(ms[0], ms[1], (30, 31) if ms[2] else (10, 10))
            m2[2], m2[3] = lock
            m3 = swap(m2)
            want = cells_ref.bane2(v, m2)
            got = self.p(v, m3)
            if EN in types and want[1] != 4:                   # v2.2's first bite (16 / 15)
                self.assertEqual(want[1:], (16, 15), case)
                self.assertEqual(got, (want[0], 12, 11), case)
                first += 1
            else:
                self.assertEqual(got, want, case)
                hits += want[1] == 4
            self.assertEqual(bytes(swap(m3)), bytes(m2), case)
        self.assertGreater(first, 1000)
        self.assertGreater(hits, 1000)


class Bane3GenTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, CELLS_DIR)
        import gen_bane3
        import gen_covetous
        self.g, self.c = gen_bane3, gen_covetous

    def test_committed_asm_is_the_generator_output(self):
        with open(os.path.join(CELLS_DIR, 'bane3.asm'), newline='') as f:
            self.assertEqual(f.read(), self.g.generate())

    def test_gate1_lines_are_banes(self):
        def gate(name):
            txt = open(os.path.join(CELLS_DIR, name)).read()
            a = txt.index('slow:')
            return txt[txt.index('\n', a):txt.index('\tjz\t\tboxed')]
        self.assertEqual(gate('bane3.asm'), gate('bane.asm'))

    def test_lock2_table(self):
        bite = self.c.bite_table()
        tbl = self.g.lock2_table()
        self.assertEqual(set(tbl), set(bite))
        off = cells_ref.BANE2_LOCK_OFF
        for mask, act in bite.items():
            self.assertEqual(tbl[mask], act | off[act & 3] << 8)

    def test_bite_lines(self):
        src = open(os.path.join(CELLS_DIR, 'bane3.asm')).read()
        start = src[src.index('\nstart:\n'):src.index('\nslow:')]
        self.assertIn('byte [abs CELLMEM_BASE + 3]', start)           # the square is read from [3]
        self.assertIn('al, [abs CELLMEM_BASE + 2]', start)            # the action from [2]
        self.assertIn('ax, [abs lock2_tbl + rcx*2]', start)
        sl = src[src.index('\nsetlock:\n'):]
        sl = sl[:sl.index('\tret')]
        self.assertIn('[abs CELLMEM_BASE + 2], ax', sl)
        self.assertEqual(sum(1 for l in sl.splitlines() if l.startswith('\t')), 1)

    def test_paste_rules(self):
        src = open(os.path.join(CELLS_DIR, 'bane3.asm')).read()
        code = '\n'.join(l.split(';')[0] for l in src.splitlines())
        for word in ('org ', 'bits ', 'section', '%include', 'rdx', 'cmove'):
            self.assertNotIn(word, code)


if __name__ == '__main__':
    unittest.main()
