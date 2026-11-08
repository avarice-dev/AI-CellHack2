"""Decode and execute VEX `vpcmpeqb xmm, xmm, xmm/m128` in Python, for cells/check_cells.py's Unicorn runner.

Unicorn 2.1.4 (QEMU 5 based) ignores the VEX vvvv register: it runs `vpcmpeqb xmm0, xmm3, [k]` as
xmm0 = (xmm0 == k), and `vpcmpeqb xmm1, xmm3, xmm4` gave all zeros (probe 2026-11-08).  So the runner's code hook
decodes every VEX instruction here, executes it itself and moves rip past it.  Only vpcmpeqb (VEX.128.66.0F 74,
the one VEX op our cells use) is supported; any other VEX instruction raises UnsupportedVex, so nothing VEX is ever
run by Unicorn's wrong semantics without notice.  Pure Python, no I/O: unit-tested in sim/tests/test_vex_emu.py.
"""

GPR = ('rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi',
       'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')


class UnsupportedVex(Exception):
    pass


class Insn(object):
    __slots__ = ('length', 'op', 'dst', 'src1', 'src2')

    def __init__(self, length, op, dst, src1, src2):
        self.length, self.op, self.dst, self.src1, self.src2 = length, op, dst, src1, src2


def _s8(b):
    return b - 256 if b > 127 else b


def _s32(bs):
    return int.from_bytes(bs, 'little', signed=True)


def decode(code):
    """Insn for a VEX vpcmpeqb at the start of `code` (>= 15 bytes is always enough), None if the first byte is
    not a VEX prefix (C4/C5 are always VEX in 64-bit mode).  src2 is ('xmm', n) or
    ('mem', base, index, scale, disp, rip_relative)."""
    if not code or code[0] not in (0xC4, 0xC5):
        return None
    if code[0] == 0xC5:
        b1 = code[1]
        r, x, b, mmmmm = (~b1 >> 7) & 1, 0, 0, 1
        vvvv, l, pp = (~b1 >> 3) & 15, (b1 >> 2) & 1, b1 & 3
        p = 2
    else:
        b1, b2 = code[1], code[2]
        r, x, b, mmmmm = (~b1 >> 7) & 1, (~b1 >> 6) & 1, (~b1 >> 5) & 1, b1 & 31
        vvvv, l, pp = (~b2 >> 3) & 15, (b2 >> 2) & 1, b2 & 3
        p = 3
    opc = code[p]
    if not (mmmmm == 1 and pp == 1 and l == 0 and opc == 0x74):
        raise UnsupportedVex('VEX op %s (map %d, pp %d, L %d, opcode %02x) is not emulated'
                             % (code[:p + 1].hex(), mmmmm, pp, l, opc))
    p += 1
    modrm = code[p]
    p += 1
    mod, reg, rm = modrm >> 6, ((modrm >> 3) & 7) | (r << 3), modrm & 7
    if mod == 3:
        return Insn(p, 'vpcmpeqb', reg, vvvv, ('xmm', rm | (b << 3)))
    base = index = None
    scale, rip = 1, False
    if rm == 4:
        sib = code[p]
        p += 1
        scale = 1 << (sib >> 6)
        ix = ((sib >> 3) & 7) | (x << 3)
        index = None if ix == 4 else GPR[ix]
        if (sib & 7) == 5 and mod == 0:
            base = None
            disp = _s32(code[p:p + 4])
            p += 4
            return Insn(p, 'vpcmpeqb', reg, vvvv, ('mem', base, index, scale, disp, False))
        base = GPR[(sib & 7) | (b << 3)]
    elif rm == 5 and mod == 0:
        disp = _s32(code[p:p + 4])
        p += 4
        return Insn(p, 'vpcmpeqb', reg, vvvv, ('mem', None, None, 1, disp, True))
    else:
        base = GPR[rm | (b << 3)]
    if mod == 1:
        disp = _s8(code[p])
        p += 1
    elif mod == 2:
        disp = _s32(code[p:p + 4])
        p += 4
    else:
        disp = 0
    return Insn(p, 'vpcmpeqb', reg, vvvv, ('mem', base, index, scale, disp, rip))


def address(src2, next_ip, read_gpr):
    _, base, index, scale, disp, rip = src2
    a = next_ip + disp if rip else disp
    if base is not None:
        a += read_gpr(base)
    if index is not None:
        a += read_gpr(index) * scale
    return a & 0xFFFFFFFFFFFFFFFF


def execute(insn, addr, read_xmm, write_xmm, read_gpr, read_mem16):
    """Run insn located at addr; read_xmm(n)/write_xmm(n, 16 bytes), read_gpr(name), read_mem16(address) -> 16
    bytes.  Returns the address of the next instruction."""
    nxt = addr + insn.length
    a = read_xmm(insn.src1)
    if insn.src2[0] == 'xmm':
        bb = read_xmm(insn.src2[1])
    else:
        bb = read_mem16(address(insn.src2, nxt, read_gpr))
    write_xmm(insn.dst, bytes(0xFF if p == q else 0 for p, q in zip(a, bb)))
    return nxt
