"""Tests of the VEX/AVX-128 variants (designs.md round 5): Woe (of Scourge), Conceit (of Covetous) and
Endemic (of Contagion).

VexRefTest: unit test of sim/cells_ref.woe / conceit / endemic; the view is faked.  Each must return its
parent's action on every view of the grid and the parent's instruction count minus the instructions the
VEX form saves on that path (traced by hand from the generators' asm: Woe/Endemic -1 after the bite,
Endemic -3 on the boxed block from the grab gate on, Conceit -1 on every path through the split check).
VexGenTest: unit test of cells/gen_woe.py, gen_conceit.py, gen_endemic.py: tables equal to the parent's
(Woe's bite table is the parent's shifted one lane), the source obeys the paste rules, uses only
instructions on the site's allow-list (cells/check_cells.py ALLOWED), and has no legacy-SSE memory
operand that would need 16-byte alignment.
VexMatchTest: integration test, real engine + the variants + real bots, nothing faked.
"""

import importlib.util
import itertools
import os
import sys
import unittest

from .helpers import E, SIM_DIR
import cells_ref
import policies

CELLS_DIR = os.path.join(os.path.dirname(SIM_DIR), 'cells')
EM, FR, EN, WA = E.CELL_EMPTY, E.CELL_FRIEND, E.CELL_ENEMY, E.CELL_WALL
ADJ = (7, 13, 17, 11)


def load(name):
    if CELLS_DIR not in sys.path:
        sys.path.insert(0, CELLS_DIR)
    spec = importlib.util.spec_from_file_location(name, os.path.join(CELLS_DIR, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class View(object):
    def __init__(self, energy, types, far=(), tick=0, pat=(20, 20, 20, 20), pos=(30, 31)):
        self.energy, self.tick = energy, tick
        self.cells = [EM] * 25
        self.cells[12] = FR
        self.energies = [0] * 25
        self.energies[12] = energy
        for i, t, pe in zip(ADJ, types, pat):
            self.cells[i] = t
            if t in (FR, EN):
                self.energies[i] = pe
        for i in far:
            self.cells[i] = EN
            self.energies[i] = 9
        self.x, self.y, self.w, self.h = pos[0], pos[1], 64, 64


FARS = ((), (0,), (2,), (22,), (6,), (8,), (14,), (18,), (6, 18))
PATS = ((20, 20, 20, 20), (12, 30, 13, 9), (4, 4, 3, 2), (47, 46, 48, 50))


def grid():
    for types in itertools.product((EM, FR, EN, WA), repeat=4):
        for e in (0, 4, 5, 8, 11, 12, 15, 16, 47, 50):
            for far in FARS:
                for tick in (0, 2980):
                    for pat in (PATS if EM not in types else PATS[:1]):
                        yield View(e, types, far, tick, pat)


def saved(name, v):
    """Instructions the VEX variant saves against its parent on view v (from the asm)."""
    c = v.cells
    if any(c[i] == EN for i in ADJ):
        return 0                                   # bite: 5 either way
    empty = any(c[i] == EM for i in ADJ)
    enemy = any(c[i] == EN for i in range(25) if i != 12)
    if name == 'woe':
        return 1                                   # gate 1 reuses the bite's window
    if name == 'endemic':
        return 3 if not empty and v.energy >= cells_ref.CONTAGION_GRAB_G else 1
    # conceit: -1 on every path through the split check
    if v.energy < cells_ref.SPRINT_SPLIT_MIN:
        return 0
    if enemy and v.energy < cells_ref.SPRINT_THREAT_MIN and v.tick < cells_ref.SPRINT_LATE_TICK:
        return 0
    return 1


PAIRS = (('woe', 'scourge'), ('conceit', 'covetous'), ('endemic', 'contagion'))


class VexRefTest(unittest.TestCase):
    def test_same_action_and_fewer_instructions_than_the_parent(self):
        for name, parent in PAIRS:
            child, par = getattr(cells_ref, name), getattr(cells_ref, parent)
            n = 0
            for v in grid():
                m1, m2 = bytearray(64), bytearray(64)
                m1[1] = m2[1] = 1
                a, ia, ta = child(v, m1)
                b, ib, tb = par(v, m2)
                d = saved(name, v)
                self.assertEqual((a, ia, ta, bytes(m1)), (b, ib - d, tb - d, bytes(m2)),
                                 '%s cells=%s e=%d tick=%d' % (name, v.cells, v.energy, v.tick))
                n += 1
            self.assertGreater(n, 10000)

    def test_endemic_keeps_contagions_memory_paths(self):
        for mem0 in (bytes([0, 0]), bytes([0, 3, 30, 31, 1, 4]), bytes([0, 3, 9, 31, 3, 0])):
            v = View(20, (EM, FR, FR, FR))
            m1, m2 = bytearray(64), bytearray(64)
            m1[:len(mem0)] = m2[:len(mem0)] = mem0
            a = cells_ref.endemic(v, m1)
            b = cells_ref.contagion(v, m2)
            self.assertEqual((a[0], a[1], bytes(m1)), (b[0], b[1] - 1, bytes(m2)))

    def test_main_path_counts(self):
        self.assertEqual(cells_ref.woe(View(12, (EM, FR, FR, FR), far=(6,)), None), (0x20, 10, 9))  # refill
        self.assertEqual(cells_ref.woe(View(30, (EM, FR, FR, FR)), None), (0x20, 10, 9))           # split
        self.assertEqual(cells_ref.woe(View(10, (FR, FR, FR, EN)), None)[1:], (5, 4))              # bite
        self.assertEqual(cells_ref.conceit(View(10, (FR, FR, EM, FR)), None), (0x22, 21, 21))      # split
        self.assertEqual(cells_ref.endemic(View(12, (FR, FR, EM, FR), far=(18,)), None), (0x22, 10, 9))

    def test_registered_as_policies(self):
        for name, _ in PAIRS:
            self.assertIs(policies.get(name), getattr(cells_ref, name))


class VexGenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check = load('check_cells')
        cls.gens = {n: load('gen_' + n) for n in ('woe', 'conceit', 'endemic')}
        cls.srcs = {n: g.generate() for n, g in cls.gens.items()}

    def test_sources_match_the_committed_asm(self):
        for n, src in self.srcs.items():
            with open(os.path.join(CELLS_DIR, n + '.asm'), newline='') as f:
                self.assertEqual(f.read(), src, n)

    def test_paste_rules_and_allowed_instructions(self):
        for n, src in self.srcs.items():
            self.assertLess(len(src.encode()), 64 * 1024, n)
            self.assertIn('VEX variant of', src.splitlines()[0], n)
            ops = self.check.mnemonics(src)
            self.assertIn('vpcmpeqb', ops, n)
            self.assertEqual(ops - self.check.ALLOWED, set(), n)
            self.assertEqual(self.check.legacy_sse_memory(src), [], n)
            self.assertNotIn('align', ops, n)

    def test_allow_list_rejects_what_the_site_faults_on(self):
        for bad in ('popcnt eax, ecx', 'pshufb xmm0, xmm1', 'vpshufb xmm0, xmm1, xmm2', 'ptest xmm0, xmm1',
                    'vptest xmm0, xmm1', 'crc32 eax, ecx', 'pext eax, ecx, edx', 'andn eax, ecx, edx',
                    'vpcmpeqb ymm0, ymm1, ymm2'):
            src = 'start:\n\t%s\n\tret\n' % bad
            self.assertTrue(self.check.mnemonics(src) - self.check.ALLOWED or 'ymm' in bad
                            and self.check.uses_ymm(src), bad)

    def test_checker_rejects_vex_dst_not_first_source(self):
        # calib-s (2026-11-08): on the site a VEX op ignores its first source and uses the old destination, so a
        # cell may only use VEX forms with destination == first source.
        for bad in ('vpcmpeqb xmm0, xmm3, [kEnemy]', 'vpcmpeqb\txmm2, xmm0, xmm1', 'vpxor xmm1, xmm2, xmm1'):
            self.assertTrue(self.check.vex_dst_not_src1('start:\n\t%s\n\tret\n' % bad), bad)
        for ok in ('vpcmpeqb xmm1, xmm1, [kTwoLo]', 'vpmovmskb eax, xmm0', 'pcmpeqb xmm0, [k]',
                   '; vpcmpeqb xmm0, xmm3, xmm1 in a comment'):
            self.assertEqual(self.check.vex_dst_not_src1('start:\n\t%s\n\tret\n' % ok), [], ok)

    def test_round5_variants_are_flagged_broken(self):
        for n, src in self.srcs.items():
            self.assertNotEqual(self.check.vex_dst_not_src1(src), [], n)

    def test_tables_equal_the_parents(self):
        import gen_covetous, gen_scourge
        woe, conceit, endemic = self.gens['woe'], self.gens['conceit'], self.gens['endemic']
        self.assertEqual(woe.bite_table(), {m << 1: a for m, a in gen_covetous.bite_table().items()})
        self.assertEqual(endemic.bite_table(), woe.bite_table())
        self.assertEqual(conceit.bite_table(), gen_covetous.bite_table())
        for g in (woe, endemic):
            self.assertEqual(g.refill_tables(), gen_scourge.refill_tables())


class VexMatchTest(unittest.TestCase):
    def test_variants_play_a_match(self):
        import bots
        eng = E.Engine([cells_ref.woe, cells_ref.conceit, cells_ref.endemic, bots.hunter], width=64, height=64,
                       seed=3, max_ticks=150)
        eng.run()
        for c in range(3):
            self.assertEqual(eng.faults[c], {})
            self.assertGreater(eng.pop[c], 20)


if __name__ == '__main__':
    unittest.main()
