"""Unit tests of cells/vex_emu.py: decoding and executing VEX vpcmpeqb outside Unicorn (no I/O; byte strings are
NASM 3.01's encodings, copied from its listing).

Why: Unicorn 2.1.4 ignores the VEX vvvv register: it runs `vpcmpeqb xmm0, xmm3, [k]` as xmm0 = (xmm0 == k) and the
register form gave all zeros (probe 2026-11-08), so cells/check_cells.py emulates vpcmpeqb itself; since calib-s
(Sandbox 104136) it emulates the SITE's behaviour, which has the same bug: dst = (old dst == src2), vvvv ignored.
"""

import importlib.util
import os
import unittest

from .helpers import SIM_DIR


def load():
    path = os.path.join(os.path.dirname(SIM_DIR), 'cells', 'vex_emu.py')
    spec = importlib.util.spec_from_file_location('vex_emu', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = load()
H = bytes.fromhex

CASES = [   # (encoding, length, dst, src1, src2)
    (H('C5E1740552000000'), 8, 0, 3, ('mem', None, None, 1, 0x52, True)),
    (H('C5F1741D3A000000'), 8, 3, 1, ('mem', None, None, 1, 0x3A, True)),
    (H('C5F9744727'), 5, 0, 0, ('mem', 'rdi', None, 1, 39, False)),
    (H('C5F174C2'), 4, 0, 1, ('xmm', 2)),
    (H('C44119748C8834120000'), 10, 9, 12, ('mem', 'r8', 'rcx', 4, 0x1234, False)),
    (H('C4410974FD'), 5, 15, 14, ('xmm', 13)),
    (H('C5D1741424'), 5, 2, 5, ('mem', 'rsp', None, 1, 0, False)),
    (H('C5D1745500'), 5, 2, 5, ('mem', 'rbp', None, 1, 0, False)),
    (H('C4815174546500'), 7, 2, 5, ('mem', 'r13', 'r12', 2, 0, False)),
    (H('C5D174142520003000'), 9, 2, 5, ('mem', None, None, 1, 0x300020, False)),
]


class DecodeTest(unittest.TestCase):
    def test_vpcmpeqb_forms(self):
        for enc, n, dst, src1, src2 in CASES:
            d = V.decode(enc + b'\x90' * 6)
            self.assertEqual((d.length, d.op, d.dst, d.src1, d.src2), (n, 'vpcmpeqb', dst, src1, src2), enc.hex())

    def test_not_vex_is_none(self):
        self.assertIsNone(V.decode(H('660F74C1')))          # legacy pcmpeqb xmm0, xmm1
        self.assertIsNone(V.decode(H('C3')))

    def test_other_vex_ops_are_refused(self):
        for enc in (H('C5F1EFC9'), H('C5F9D7C1'), H('C4E2710000'), H('C5F574C2')):   # vpxor, vpmovmskb, vpshufb, ymm
            with self.assertRaises(V.UnsupportedVex):
                V.decode(enc + b'\x90' * 6)


class ExecuteTest(unittest.TestCase):
    def setUp(self):
        self.xmm = {i: bytes([0x5A] * 16) for i in range(16)}
        self.gpr = {'rdi': 0x300000, 'r8': 0x1000, 'rcx': 3, 'rsp': 0x200000}
        self.mem = {}

    def run_one(self, enc, addr=0x100000):
        return V.execute(V.decode(enc + b'\x90' * 6), addr, self.xmm.__getitem__, self.xmm.__setitem__,
                         self.gpr.__getitem__, lambda a: self.mem[a])

    def test_memory_compare_uses_old_dst_like_the_site(self):
        # Until calib-s this expected the documented form (xmm3 compared); the site compares the old xmm0.
        self.xmm[3] = bytes([2, 2, 2, 2] + [0] * 12)
        self.xmm[0] = bytes([2, 9] * 8)                    # the site (and Unicorn) compare this one
        self.mem[0x100000 + 8 + 0x52] = bytes([2] * 16)
        nxt = self.run_one(H('C5E1740552000000'))        # vpcmpeqb xmm0, xmm3, [rip + 0x52]
        self.assertEqual(nxt, 0x100008)
        self.assertEqual(self.xmm[0], bytes([0xFF, 0] * 8))
        self.assertEqual(self.xmm[3], bytes([2, 2, 2, 2] + [0] * 12))

    def test_site_semantics_compare_uses_old_dst_and_ignores_src1(self):
        # calib-s (Sandbox 104136, 2026-11-08): the site's QEMU runs `vpcmpeqb xmm2, xmm0, xmm1` as
        # xmm2 = (xmm2 == xmm1): the first source (VEX.vvvv) is ignored, the old destination is compared.
        self.xmm[2] = bytes([7, 0, 7, 0] + [1] * 12)       # old destination
        self.xmm[0] = bytes([3] * 16)                      # first source: must not matter
        self.xmm[1] = bytes([7, 7, 0, 0] + [1] * 12)
        self.run_one(H('C5F974D1'))                        # vpcmpeqb xmm2, xmm0, xmm1
        self.assertEqual(self.xmm[2], bytes([0xFF, 0, 0, 0xFF] + [0xFF] * 12))
        self.assertEqual(self.xmm[0], bytes([3] * 16))

    def test_register_form_and_displacement(self):
        self.xmm[1] = bytes(range(16))
        self.xmm[2] = bytes([0, 1, 0, 3] + [99] * 12)
        self.run_one(H('C5F174C2'))                        # vpcmpeqb xmm0, xmm1, xmm2: old xmm0 (0x5A) == xmm2
        self.assertEqual(self.xmm[0], bytes([0] * 16))
        self.xmm[0] = bytes([0] * 16)
        self.mem[0x300000 + 39] = bytes([0, 1] * 8)        # unaligned is fine
        self.run_one(H('C5F9744727'))
        self.assertEqual(self.xmm[0], bytes([0xFF, 0] * 8))

    def test_sib_address(self):
        self.xmm[9] = bytes([7] * 16)                      # old destination (the site ignores xmm12)
        self.xmm[12] = bytes([6] * 16)
        self.mem[0x1000 + 3 * 4 + 0x1234] = bytes([7] * 8 + [6] * 8)
        self.run_one(H('C44119748C8834120000'))
        self.assertEqual(self.xmm[9], bytes([0xFF] * 8 + [0] * 8))


if __name__ == '__main__':
    unittest.main()
