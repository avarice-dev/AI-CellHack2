"""Assemble our cells exactly like the server and check them; optionally diff Sprint against the
Python reference in Unicorn.  Run inside WSL (needs nasm; Unicorn optional):

    cd <repo root, as seen from WSL>
    $HOME/cellhack-venv/bin/python cells/check_cells.py            # assemble + static checks (+ diff if unicorn)

For each cells/*.asm and cells/calib/*.asm a temp copy is built as
    bits 64 / org 0x00100000 / default rel / <docs/cellhack.inc> / <the source> / [map symbols ...]
(the map line exists only in the temp copy) and assembled with `nasm -f bin -l`.  Outputs (bin, listing,
map) go to cells/build/ (git-ignored).

Checks: source <= 64 KB, binary <= CODE_MAX; the source has no org/bits/section/%include; for sprint:
SSE constants 16-byte aligned, no 0xCC byte inside fight_tbl/split_tbl, every fight_tbl entry points at
one of slow/eat_*/stub, the table jmp is encoded FF 24 C5 disp32 (absolute, no RIP-relative), split_tbl
holds only valid actions.  With Unicorn: every calibration cell's instruction count, and Sprint vs
sim/cells_ref.sprint over all 4^4 adjacent types x energies {0,4,5,15,16,50} x enemy at distance 2
on/off x tick {0,2980}, comparing action and instruction count.  For covetous: SSE constants aligned, bite_tbl
holds only 0 or eat actions (entry 0 = 0), split_tbl only valid actions, the bite exit is `jnz rel32` to EXIT_ADDR,
and a Unicorn diff against sim/cells_ref.covetous that also varies neighbour energies.  For scourge: the same
static checks plus act_tbl (only 0 or split actions, bytes equal to gen_scourge.refill_tables()) and thr_tbl,
the gate-1 exit is `jae rel32` to EXIT_ADDR, and a Unicorn diff against sim/cells_ref.scourge that also places
enemies on the refill window's squares and on the unread squares 2 and 22.  For contagion: Scourge's checks,
its bite and gate-1 source lines verbatim (no memory access there), and a Unicorn diff against
sim/cells_ref.contagion that also varies memory state and position and compares memory after the call.
"""

import itertools
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
INC = os.path.join(ROOT, 'docs', 'cellhack.inc')
sys.path.insert(0, os.path.join(ROOT, 'sim'))
sys.path.insert(0, HERE)

CODE_BASE, CODE_SIZE, CODE_MAX = 0x100000, 0x10000, 0x8000
STACK_BASE, STACK_SIZE = 0x200000, 0x4000
VIEW_BASE, CELLMEM_BASE, EXIT_ADDR = 0x300000, 0x310000, 0x400000
VALID = {0x00, 0x01} | {b + d for b in (0x10, 0x20, 0x30, 0x40) for d in range(4)}

problems = []


def fail(msg):
    problems.append(msg)
    print('  FAIL', msg)


def assemble(src_path):
    name = os.path.splitext(os.path.basename(src_path))[0]
    src = open(src_path, 'rb').read()
    print('%s: source %d bytes' % (os.path.relpath(src_path, ROOT), len(src)))
    if len(src) > 64 * 1024:
        fail('%s source over 64 KB' % name)
    for line in src.decode().splitlines():
        code = line.split(';', 1)[0].strip().lower()
        if re.match(r'^(\[?\s*)(org|bits|section|%include|segment)\b', code):
            fail('%s contains a forbidden directive: %r' % (name, line))
    os.makedirs(BUILD, exist_ok=True)
    tmp = os.path.join(BUILD, name + '.full.asm')
    out, lst, mp = (os.path.join(BUILD, name + ext) for ext in ('.bin', '.lst', '.map'))
    with open(tmp, 'wb') as f:
        # The docs print `org CODE_BASE` before the constants, but NASM rejects that order ("symbol
        # `CODE_BASE' not defined before use"), so the server must use the literal; we do the same.
        f.write(b'bits 64\norg 0x00100000\ndefault rel\n')
        f.write(open(INC, 'rb').read())
        f.write(b'\n')
        f.write(src)
        f.write(('\n[map symbols %s]\n' % mp).encode())
    r = subprocess.run(['nasm', '-f', 'bin', '-o', out, '-l', lst, tmp], capture_output=True, text=True)
    if r.returncode:
        fail('%s: nasm failed:\n%s' % (name, r.stderr))
        return None
    if r.stderr.strip():
        print('  nasm warnings:', r.stderr.strip())
    blob = open(out, 'rb').read()
    print('  binary %d bytes' % len(blob))
    if len(blob) > CODE_MAX:
        fail('%s binary over CODE_MAX' % name)
    syms = {}
    for line in open(mp):
        m = re.match(r'^\s*([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+(\S+)\s*$', line)
        if m:
            syms[m.group(3)] = int(m.group(1), 16)
    return blob, syms, lst


def check_sprint(blob, syms, lst):
    off = {k: v - CODE_BASE for k, v in syms.items() if v >= CODE_BASE}
    for k in ('kEnemy', 'kEmpty', 'kTwoLo', 'kTwoHi'):
        if syms[k] % 16:
            fail('%s at 0x%x is not 16-byte aligned' % (k, syms[k]))
    ft, fe, st, se = off['fight_tbl'], off['fight_tbl_end'], off['split_tbl'], off['split_tbl_end']
    if fe - ft != 1106 * 8 or se - st != 1106:
        fail('table sizes %d / %d' % (fe - ft, se - st))
    for a, b, n in ((ft, fe, 'fight_tbl'), (st, se, 'split_tbl')):
        if 0xCC in blob[a:b]:
            fail('0xCC inside %s at +%d' % (n, blob.index(0xCC, a) - a))
    targets = {syms[k] for k in ('slow', 'eat_up', 'eat_right', 'eat_down', 'eat_left', 'stub')}
    ents = struct.unpack('<1106Q', blob[ft:fe])
    bad = [i for i, e in enumerate(ents) if e not in targets]
    if bad:
        fail('fight_tbl entries with bad targets: %s' % bad[:10])
    if ents[0] != syms['slow']:
        fail('fight_tbl[0] is not slow')
    badact = [i for i, b in enumerate(blob[st:se]) if b not in VALID]
    if badact:
        fail('split_tbl invalid actions at %s' % badact[:10])
    jline = [l for l in open(lst) if re.search(r'jmp\s+\[abs fight_tbl', l)]
    if not jline or 'FF24C5' not in jline[0].replace(' ', '').upper():
        fail('table jmp not encoded as FF 24 C5 disp32: %r' % jline)
    else:
        print('  jmp listing:', ' '.join(jline[0].split()[:3]))
    print('  constants at', ', '.join('%s=0x%x' % (k, syms[k]) for k in ('kEnemy', 'kEmpty', 'kTwoLo', 'kTwoHi')))
    print('  fight_tbl 0x%x..0x%x, split_tbl 0x%x..0x%x' % (syms['fight_tbl'], syms['fight_tbl_end'],
                                                          syms['split_tbl'], syms['split_tbl_end']))


class Runner(object):
    def __init__(self, blob):
        import unicorn as U
        import unicorn.x86_const as X
        self.U, self.X = U, X
        uc = U.Uc(U.UC_ARCH_X86, U.UC_MODE_64)
        uc.mem_map(CODE_BASE, CODE_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
        uc.mem_write(CODE_BASE, blob + b'\xcc' * (CODE_SIZE - len(blob)))
        uc.mem_map(STACK_BASE, STACK_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
        uc.mem_map(VIEW_BASE, 0x1000, U.UC_PROT_READ)
        uc.mem_map(CELLMEM_BASE, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        uc.mem_map(EXIT_ADDR, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        try:
            uc.reg_write(X.UC_X86_REG_CR4, uc.reg_read(X.UC_X86_REG_CR4) | 0x600)   # OSFXSR, OSXMMEXCPT
        except Exception:
            pass
        self.n = 0

        def hook(uc_, addr, size, ud):
            self.n += 1
        uc.hook_add(U.UC_HOOK_CODE, hook, begin=CODE_BASE, end=CODE_BASE + CODE_SIZE - 1)
        self.uc = uc

    def call(self, view_bytes, energy, rax=0, mem=None):
        uc, X = self.uc, self.X
        uc.mem_write(VIEW_BASE, view_bytes.ljust(0x1000, b'\0'))
        if mem is not None:
            uc.mem_write(CELLMEM_BASE, bytes(mem))
        uc.mem_write(STACK_BASE, b'\0' * STACK_SIZE)
        uc.mem_write(STACK_BASE + STACK_SIZE - 8, struct.pack('<Q', EXIT_ADDR))
        uc.mem_write(CELLMEM_BASE + 64, b'\0' * (0x1000 - 64))
        for r in (X.UC_X86_REG_RAX, X.UC_X86_REG_RBX, X.UC_X86_REG_RCX, X.UC_X86_REG_R8):
            uc.reg_write(r, 0)
        uc.reg_write(X.UC_X86_REG_RAX, rax)
        uc.reg_write(X.UC_X86_REG_RDI, VIEW_BASE)
        uc.reg_write(X.UC_X86_REG_RSI, energy)
        uc.reg_write(X.UC_X86_REG_RDX, CELLMEM_BASE)
        uc.reg_write(X.UC_X86_REG_RSP, STACK_BASE + STACK_SIZE - 8)
        self.n = 0
        uc.emu_start(CODE_BASE, EXIT_ADDR, count=2000)
        if uc.reg_read(X.UC_X86_REG_RIP) != EXIT_ADDR:
            raise RuntimeError('did not return (rip 0x%x)' % uc.reg_read(X.UC_X86_REG_RIP))
        return uc.reg_read(X.UC_X86_REG_RAX) & 0xFF, self.n


def view_bytes(tick, energy, cells, energies=None, xywh=None):
    b = bytearray(128)
    struct.pack_into('<I', b, 0, tick)
    b[4] = energy
    if xywh is not None:
        struct.pack_into('<4H', b, 8, *xywh)
    b[32:57] = bytes(cells)
    if energies is not None:
        b[64:89] = bytes(energies)
    return bytes(b)


class V(object):
    pass


def diff_sprint(blob):
    import cells_ref
    r = Runner(blob)
    adj = (7, 13, 17, 11)               # UP RIGHT DOWN LEFT
    n = mism = 0
    for types in itertools.product(range(4), repeat=4):
        for energy in (0, 4, 5, 15, 16, 50):
            for far in (None, 0, 2, 14, 24):  # far enemy on/off (several distance-2 squares)
                for tick in (0, 2980):
                    cells = [0] * 25
                    cells[12] = 1
                    for i, t in zip(adj, types):
                        cells[i] = t
                    if far is not None:
                        cells[far] = 2
                    v = V()
                    v.cells, v.energy, v.tick = cells, energy, tick
                    want = cells_ref.sprint(v, bytearray(64))[:2]
                    got = r.call(view_bytes(tick, energy, cells), energy)
                    n += 1
                    if got != want:
                        mism += 1
                        if mism <= 10:
                            fail('sprint diff types=%s e=%d far=%s tick=%d: asm %s ref %s'
                                 % (types, energy, far, tick, got, want))
    print('  unicorn diff: %d cases, %d mismatches' % (n, mism))


def check_covetous(blob, syms, lst):
    off = {k: v - CODE_BASE for k, v in syms.items() if v >= CODE_BASE}
    for k in ('kEnemy', 'kEmpty', 'kTwoLo', 'kTwoHi'):
        if syms[k] % 16:
            fail('covetous %s at 0x%x is not 16-byte aligned' % (k, syms[k]))
    bt, be, st, se = off['bite_tbl'], off['bite_tbl_end'], off['split_tbl'], off['split_tbl_end']
    if be - bt != 1106 or se - st != 1106:
        fail('covetous table sizes %d / %d' % (be - bt, se - st))
    if blob[bt] != 0:
        fail('covetous bite_tbl[0] is not 0')
    bad = [i for i, b in enumerate(blob[bt:be]) if b != 0 and not 0x30 <= b <= 0x33]
    if bad:
        fail('covetous bite_tbl entries neither 0 nor an eat: %s' % bad[:10])
    badact = [i for i, b in enumerate(blob[st:se]) if b not in VALID]
    if badact:
        fail('covetous split_tbl invalid actions at %s' % badact[:10])
    # bite exit: the 6 bytes before `slow` must be jnz rel32 (0F 85) whose target is EXIT_ADDR
    j = off['slow'] - 6
    code = blob[j:j + 6]
    ok = code[:2] == b'\x0f\x85' and CODE_BASE + j + 6 + struct.unpack('<i', code[2:6])[0] == EXIT_ADDR
    if not ok:
        fail('covetous: bite exit is not `jnz rel32` to EXIT_ADDR: %s' % code.hex())
    else:
        print('  bite exit: %s at 0x%x -> 0x%x' % (code.hex(' '), CODE_BASE + j, EXIT_ADDR))
    print('  constants at', ', '.join('%s=0x%x' % (k, syms[k]) for k in ('kEnemy', 'kEmpty', 'kTwoLo', 'kTwoHi')))


def diff_covetous(blob):
    """Covetous vs sim/cells_ref.covetous: all 4^4 adjacent types x energies x far enemy x tick x
    friend-energy patterns (equal, one poorer, ties, rich)."""
    import cells_ref
    r = Runner(blob)
    adj = (7, 13, 17, 11)               # UP RIGHT DOWN LEFT
    pats = ((20, 20, 20, 20), (20, 5, 9, 5), (50, 40, 1, 0), (47, 46, 48, 50), (47, 47, 47, 47), (46, 50, 46, 9))
    n = mism = 0
    for types in itertools.product(range(4), repeat=4):
        for energy in (0, 4, 5, 15, 16, 46, 47, 50):
            for far in (None, 0, 14, 24):
                for tick in (0, 2980):
                    for pat in pats:
                        cells = [0] * 25
                        cells[12] = 1
                        ens = [0] * 25
                        ens[12] = energy
                        for i, t, pe in zip(adj, types, pat):
                            cells[i] = t
                            if t in (1, 2):
                                ens[i] = pe
                        if far is not None:
                            cells[far] = 2
                            ens[far] = 9
                        v = V()
                        v.cells, v.energy, v.tick, v.energies = cells, energy, tick, ens
                        want = cells_ref.covetous(v, bytearray(64))[:2]
                        got = r.call(view_bytes(tick, energy, cells, ens), energy)
                        n += 1
                        if got != want:
                            mism += 1
                            if mism <= 10:
                                fail('covetous diff types=%s e=%d far=%s tick=%d pat=%s: asm %s ref %s'
                                     % (types, energy, far, tick, pat, got, want))
    print('  unicorn diff: %d cases, %d mismatches' % (n, mism))


def check_scourge(blob, syms, lst):
    import gen_scourge
    off = {k: v - CODE_BASE for k, v in syms.items() if v >= CODE_BASE}
    for k in ('kEnemy', 'kRefill', 'kTwoLo', 'kTwoHi'):
        if syms[k] % 16:
            fail('scourge %s at 0x%x is not 16-byte aligned' % (k, syms[k]))
    n = gen_scourge.N_REFILL
    bt, be = off['bite_tbl'], off['bite_tbl_end']
    at, ae, tt, te = off['act_tbl'], off['act_tbl_end'], off['thr_tbl'], off['thr_tbl_end']
    if be - bt != 1106 or ae - at != n or te - tt != n:
        fail('scourge table sizes %d / %d / %d' % (be - bt, ae - at, te - tt))
    if blob[bt] != 0:
        fail('scourge bite_tbl[0] is not 0')
    bad = [i for i, b in enumerate(blob[bt:be]) if b != 0 and not 0x30 <= b <= 0x33]
    if bad:
        fail('scourge bite_tbl entries neither 0 nor an eat: %s' % bad[:10])
    bad = [i for i, b in enumerate(blob[at:ae]) if b != 0 and not 0x20 <= b <= 0x23]
    if bad:
        fail('scourge act_tbl entries neither 0 nor a split: %s' % bad[:10])
    act, thr = gen_scourge.refill_tables()
    if any(blob[at + m] != a for m, a in act.items()) or any(blob[tt + m] != t for m, t in thr.items()):
        fail('scourge act_tbl/thr_tbl bytes differ from gen_scourge.refill_tables()')
    j = off['slow'] - 6
    code = blob[j:j + 6]
    if not (code[:2] == b'\x0f\x85' and CODE_BASE + j + 6 + struct.unpack('<i', code[2:6])[0] == EXIT_ADDR):
        fail('scourge: bite exit is not `jnz rel32` to EXIT_ADDR: %s' % code.hex())
    jl = [l for l in open(lst) if re.search(r'\bjae\s+EXIT_ADDR\s+;\s*refill', l)]
    if not jl or not jl[0].split()[2].upper().startswith('0F83'):
        fail('scourge: gate-1 exit not `jae rel32`: %r' % jl)
    print('  bite exit: %s; constants at %s' % (code.hex(' '), ', '.join(
        '%s=0x%x' % (k, syms[k]) for k in ('kEnemy', 'kRefill', 'kTwoLo', 'kTwoHi'))))


def diff_scourge(blob):
    """Scourge vs sim/cells_ref.scourge: all 4^4 adjacent types x energies x enemy placements (refill
    window squares, unread squares 2/22, corners, pairs) x tick x friend-energy patterns."""
    import cells_ref
    r = Runner(blob)
    adj = (7, 13, 17, 11)               # UP RIGHT DOWN LEFT
    pats = ((20, 20, 20, 20), (12, 30, 13, 9), (50, 40, 1, 0), (47, 46, 48, 50), (42, 46, 43, 46))
    fars = ((), (0,), (24,), (2,), (22,), (6,), (8,), (10,), (14,), (16,), (18,), (6, 18), (2, 22, 9))
    n = mism = 0
    for types in itertools.product(range(4), repeat=4):
        for energy in (0, 4, 5, 11, 12, 15, 16, 46, 47, 50):
            for far in fars:
                for tick in (0, 2980):
                    for pat in (pats if energy >= 16 and 0 not in types else pats[:1]):
                        cells = [0] * 25
                        cells[12] = 1
                        ens = [0] * 25
                        ens[12] = energy
                        for i, t, pe in zip(adj, types, pat):
                            cells[i] = t
                            if t in (1, 2):
                                ens[i] = pe
                        for i in far:
                            cells[i] = 2
                            ens[i] = 9
                        v = V()
                        v.cells, v.energy, v.tick, v.energies = cells, energy, tick, ens
                        want = cells_ref.scourge(v, bytearray(64))[:2]
                        got = r.call(view_bytes(tick, energy, cells, ens), energy)
                        n += 1
                        if got != want:
                            mism += 1
                            if mism <= 10:
                                fail('scourge diff types=%s e=%d far=%s tick=%d pat=%s: asm %s ref %s'
                                     % (types, energy, far, tick, pat, got, want))
    print('  unicorn diff: %d cases, %d mismatches' % (n, mism))


def check_contagion(blob, syms, lst):
    """Scourge's static checks, plus: the bite and gate-1 source lines are Scourge's verbatim."""
    import gen_scourge
    check_scourge(blob, syms, lst)
    def fast(path):
        txt = open(path).read()
        return txt[txt.index('start:'):txt.index('	test		al, al')]
    if fast(os.path.join(HERE, 'contagion.asm')) != fast(os.path.join(HERE, 'scourge.asm')):
        fail('contagion: bite / gate-1 source differs from scourge.asm')
    gate = fast(os.path.join(HERE, 'contagion.asm'))
    if 'rdx' in gate:
        fail('contagion: bite / gate-1 path touches the cell memory')
    print('  bite + gate-1 source identical to scourge.asm (%d instructions)'
          % sum(1 for l in gate.splitlines() if l.startswith('	') and l.strip()))


def diff_contagion(blob):
    """Contagion vs sim/cells_ref.contagion: Scourge's grid of adjacent types x energies x enemy placements x
    tick x friend-energy patterns, under several memory states (plain, start cell, scout at / off origin, out of
    steps) and positions (centre, near each edge), comparing action, instruction count and memory after."""
    import cells_ref
    r = Runner(blob)
    adj = (7, 13, 17, 11)               # UP RIGHT DOWN LEFT
    pats = ((20, 20, 20, 20), (12, 30, 13, 9), (50, 40, 1, 0), (47, 46, 48, 50), (4, 4, 3, 2), (8, 2, 30, 4))
    fars = ((), (0,), (24,), (2,), (22,), (6,), (8,), (10,), (14,), (16,), (18,), (6, 18), (2, 22, 9))
    rings = ((), (1, 2, 3, 4, 5, 6, 8, 9, 10, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24))   # ring squares friend
    mems = (bytes([0, 1]), bytes([0, 0]), bytes([0, 3, 30, 31, 1, 4]), bytes([0, 3, 30, 30, 2, 7]),
            bytes([0, 3, 9, 31, 3, 0]))
    poss = ((30, 31), (3, 31), (60, 31), (30, 2), (30, 61), (11, 11))
    n = mism = 0
    for types in itertools.product(range(4), repeat=4):
        for energy in (0, 4, 5, 7, 8, 11, 12, 15, 16, 46, 47, 50):
            for far in fars:
                for tick in (0, 2980):
                    for ring in (rings if 0 not in types else rings[:1]):
                        for pat in (pats if energy >= 8 and 0 not in types else pats[:1]):
                            for mi, m0 in enumerate(mems if len(far) <= 1 and far in ((), (0,), (8,)) else mems[:1]):
                                for pos in (poss if mi and 0 in types and not far else poss[:1]):
                                    cells = [0] * 25
                                    cells[12] = 1
                                    for i in ring:
                                        cells[i] = 1
                                    ens = [0] * 25
                                    ens[12] = energy
                                    for i, t, pe in zip(adj, types, pat):
                                        cells[i] = t
                                        if t in (1, 2):
                                            ens[i] = pe
                                    for i in far:
                                        cells[i] = 2
                                        ens[i] = 9
                                    v = V()
                                    v.cells, v.energy, v.tick, v.energies = cells, energy, tick, ens
                                    v.x, v.y, v.w, v.h = pos[0], pos[1], 64, 64
                                    mref = bytearray(64)
                                    mref[:len(m0)] = m0
                                    masm = bytes(mref)
                                    want = cells_ref.contagion(v, mref)[:2]
                                    got = r.call(view_bytes(tick, energy, cells, ens, (pos[0], pos[1], 64, 64)),
                                                 energy, mem=masm)
                                    gmem = bytes(r.uc.mem_read(CELLMEM_BASE, 64))
                                    n += 1
                                    if got != want or gmem != bytes(mref):
                                        mism += 1
                                        if mism <= 10:
                                            fail('contagion diff types=%s e=%d far=%s tick=%d ring=%d pat=%s mem=%s '
                                                 'pos=%s: asm %s %s ref %s %s'
                                                 % (types, energy, far, tick, len(ring), pat, m0.hex(), pos, got,
                                                    gmem[:6].hex(), want, bytes(mref[:6]).hex()))
    print('  unicorn diff: %d cases, %d mismatches' % (n, mism))


def main():
    files = sorted(os.path.join(HERE, f) for f in os.listdir(HERE) if f.endswith('.asm'))
    files += sorted(os.path.join(HERE, 'calib', f) for f in os.listdir(os.path.join(HERE, 'calib'))
                    if f.endswith('.asm'))
    try:
        import unicorn  # noqa: F401
        have_uc = True
    except ImportError:
        have_uc = False
        print('unicorn not importable: emulator checks skipped')
    for p in files:
        res = assemble(p)
        if not res:
            continue
        blob, syms, lst = res
        name = os.path.splitext(os.path.basename(p))[0]
        if name == 'sprint':
            check_sprint(blob, syms, lst)
            if have_uc:
                diff_sprint(blob)
        elif name == 'covetous':
            check_covetous(blob, syms, lst)
            if have_uc:
                diff_covetous(blob)
        elif name == 'scourge':
            check_scourge(blob, syms, lst)
            if have_uc:
                diff_scourge(blob)
        elif name == 'contagion':
            check_contagion(blob, syms, lst)
            if have_uc:
                diff_contagion(blob)
        elif have_uc:
            base = view_bytes(5, 10, [0] * 12 + [1] + [0] * 12)
            for rax in ((0, 0x1234) if name.startswith('c_') else (0,)):
                act, n = Runner(blob).call(base, 10, rax=rax)
                print('  unicorn: rax=0x%x -> action 0x%02x, %d instructions (Unicorn hook count)' % (rax, act, n))
    print('\n%s' % ('ALL CHECKS PASSED' if not problems else '%d PROBLEM(S)' % len(problems)))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
