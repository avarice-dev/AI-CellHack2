"""Assemble our cells exactly like the server and check them; optionally diff Sprint against the
Python reference in Unicorn.  Run inside WSL (needs nasm; Unicorn optional):

    cd <repo root, as seen from WSL>
    $HOME/cellhack-venv/bin/python cells/check_cells.py            # assemble + static checks (+ diff if unicorn)

For each cells/*.asm and cells/calib/*.asm a temp copy is built as
    bits 64 / org CODE_BASE / default rel / <docs/cellhack.inc> / <the source> / [map symbols ...]
(the map line exists only in the temp copy) and assembled with `nasm -f bin -l`.  Outputs (bin, listing,
map) go to cells/build/ (git-ignored).

Checks: source <= 64 KB, binary <= CODE_MAX; the source has no org/bits/section/%include; for sprint:
SSE constants 16-byte aligned, no 0xCC byte inside fight_tbl/split_tbl, every fight_tbl entry points at
one of slow/eat_*/stub, the table jmp is encoded FF 24 C5 disp32 (absolute, no RIP-relative), split_tbl
holds only valid actions.  With Unicorn: every calibration cell's instruction count, and Sprint vs
sim/cells_ref.sprint over all 4^4 adjacent types x energies {0,4,5,15,16,50} x enemy at distance 2
on/off x tick {0,2980}, comparing action and instruction count.
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
        f.write(b'bits 64\norg CODE_BASE\ndefault rel\n')
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

    def call(self, view_bytes, energy, rax=0):
        uc, X = self.uc, self.X
        uc.mem_write(VIEW_BASE, view_bytes.ljust(0x1000, b'\0'))
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


def view_bytes(tick, energy, cells):
    b = bytearray(128)
    struct.pack_into('<I', b, 0, tick)
    b[4] = energy
    b[32:57] = bytes(cells)
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
        elif have_uc:
            base = view_bytes(5, 10, [0] * 12 + [1] + [0] * 12)
            for rax in ((0, 0x1234) if name.startswith('c_') else (0,)):
                act, n = Runner(blob).call(base, 10, rax=rax)
                print('  unicorn: rax=0x%x -> action 0x%02x, %d instructions (Unicorn hook count)' % (rax, act, n))
    print('\n%s' % ('ALL CHECKS PASSED' if not problems else '%d PROBLEM(S)' % len(problems)))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
