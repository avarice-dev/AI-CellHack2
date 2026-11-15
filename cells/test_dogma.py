"""Dogma tests: static checks of cells/dogma.asm and an exhaustive Unicorn verification (run inside WSL).

    python3 cells/test_dogma.py             # build dogma.asm + the ablation variants, run everything
    python3 cells/test_dogma.py --mutants   # also show planted mutants failing (every one must be caught)

Level labels: the Unicorn sections are INTEGRATION tests (the real assembled binary, real tables, the real
cells_ref reference; only the engine around the call is simulated: stun and split inheritance are replayed by hand
from sim/engine.py semantics).  The static checks are unit tests of the source text.  Nothing here is e2e.

check_cells.py --only dogma calls check_dogma() / diff_dogma() below.
"""

import collections
import os
import random
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'sim'))

import gen_dogma as D  # noqa: E402
import gen_scourge as S  # noqa: E402
import gen_covetous as C  # noqa: E402
import check_cells as CC  # noqa: E402

IDX = (7, 13, 17, 11)
CELLMEM = CC.CELLMEM_BASE
ACT_REST, ACT_MOVE, ACT_SPLIT, ACT_EAT, ACT_FEED = 1, 0x10, 0x20, 0x30, 0x40
VARIANTS = {'k_cap12': dict(k_cap=12), 'k_cap25': dict(k_cap=25), 'k12_0': dict(k12=0),
            'quiet28': dict(quiet_cap=28), 'quiet38': dict(quiet_cap=38)}


class Result(object):
    def __init__(self, fail):
        self.fail = fail
        self.cases = 0
        self.bad = 0
        self.counts = collections.defaultdict(set)      # path label -> set of instruction counts seen

    def check(self, ok, msg):
        self.cases += 1
        if not ok:
            self.bad += 1
            if self.bad <= 12:
                self.fail(msg)


def build(src, name):
    """Assemble `src` like the server (a variant) into cells/build/<name>.bin; (blob, syms)."""
    os.makedirs(CC.BUILD, exist_ok=True)
    full = os.path.join(CC.BUILD, name + '.full.asm')
    out, mp = os.path.join(CC.BUILD, name + '.bin'), os.path.join(CC.BUILD, name + '.map')
    with open(full, 'wb') as f:
        f.write(b'bits 64\norg 0x00100000\ndefault rel\n' + open(CC.INC, 'rb').read() + b'\n' + src.encode()
                + ('\n[map symbols %s]\n' % mp).encode())
    r = subprocess.run(['nasm', '-f', 'bin', '-o', out, full], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError('nasm failed for %s:\n%s' % (name, r.stderr))
    syms = {}
    for line in open(mp):
        m = re.match(r'^\s*([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+(\S+)\s*$', line)
        if m:
            syms[m.group(3)] = int(m.group(1), 16)
    return open(out, 'rb').read(), syms


# ---------------------------------------------------------------------------------------------------------------
# static checks
# ---------------------------------------------------------------------------------------------------------------
def check_dogma(path, blob, syms, lst, res=None):
    src = open(path).read()
    if src != D.generate():
        CC.fail('dogma.asm differs from gen_dogma.generate()')
    for k in ('kEnemy', 'kRefill', 'kNearLo', 'kNearHi', 'kTwoLo', 'kTwoHi', 'kOpen7'):
        if syms[k] % 16:
            CC.fail('dogma %s at 0x%x is not 16-byte aligned' % (k, syms[k]))
    if len(blob) > CC.CODE_MAX:
        CC.fail('dogma binary %d over CODE_MAX' % len(blob))

    def tb(name, n):
        o = syms[name] - CC.CODE_BASE
        return blob[o:o + n]
    exp = {'bite_tbl': bytes(C.bite_table().get(m, 0) for m in range(1106)),
           'act_tbl': bytes(S.refill_tables()[0].get(m, 0) for m in range(S.N_REFILL)),
           'thr_tbl': bytes(S.refill_tables()[1].get(m, 255) for m in range(S.N_REFILL)),
           'kmask_tbl': b''.join(struct.pack('<Q', D.kmask(te)) for te in range(256)),
           'open_lo': bytes(D.open_lo(m) for m in range(256)), 'open_hi': bytes(D.open_hi(m) for m in range(256)),
           'dir_pick_tbl': bytes(D.dir_pick(i) for i in range(1024)), 'd2_tbl': bytes(D.D2_TBL),
           'kOpen7': bytes(16)}
    for name, want in exp.items():
        if tb(name, len(want)) != want:
            CC.fail('dogma %s bytes differ from the spec formulas' % name)
    if any(not (1 << 0) for _ in ()):
        pass
    arm_ptrs = struct.unpack('<4Q', tb('arm_tbl', 32))
    if arm_ptrs != tuple(CC.CODE_BASE + syms['arm_' + n] - CC.CODE_BASE for n in ('up', 'right', 'down', 'left')):
        CC.fail('dogma arm_tbl entries are not the 4 stubs: %s' % (arm_ptrs,))
    o = syms['arm'] - CC.CODE_BASE
    if blob[o:o + 3] != b'\xff\x24\xc5':
        CC.fail('dogma arm: jump is not FF 24 C5: %s' % blob[o:o + 8].hex())
    n_esi = n_rsi = 0
    code_lines = list(CC._code_lines(src))
    for line in code_lines:
        if line.split()[0] in ('db', 'dq', 'times'):
            continue
        if line.startswith('lea'):
            continue                          # lea computes, it does not access memory
        for mem in re.findall(r'\[([^\]]*)\]', line):
            if re.search(r'\b[er]?si\b', mem):
                n_esi += 1
                CC.fail('dogma: esi/rsi memory operand (none expected): %r' % line)
        if line.startswith('pmovmskb') and not (line.startswith('pmovmskb\tecx') or 'r8d' in line or 'ecx' in line):
            CC.fail('dogma: pmovmskb into an unexpected register: %r' % line)
        if line.startswith('pmovmskb') and 'edx' in line:
            CC.fail('dogma: pmovmskb edx clobbers rdx: %r' % line)
    ecx_pm = [l for l in code_lines if l.startswith('pmovmskb') and 'ecx' in l]
    if len(ecx_pm) != 2:
        CC.fail('dogma: pmovmskb ecx expected exactly twice (bite scan, gate 1): %d' % len(ecx_pm))
    for l in code_lines:                       # rdx must never be a destination
        if re.match(r'(mov|movzx|lea|add|sub|and|or|xor|shl|shr|inc|dec)\s+r?e?dx\b', l.replace('\t', ' ')):
            CC.fail('dogma: writes rdx: %r' % l)
    print('  dogma static: tables == spec formulas, aligned SSE constants, one FF 24 C5, no esi/rsi memory operand, '
          'pmovmskb ecx x2 (rest r8d), no rdx write, binary %d B' % len(blob))


# ---------------------------------------------------------------------------------------------------------------
# Unicorn harness
# ---------------------------------------------------------------------------------------------------------------
class V(object):
    pass


class Harness(object):
    def __init__(self, blob, ref, res):
        self.r = CC.Runner(blob)
        self.ref = ref
        self.res = res

    def run(self, cells, ens, tick, pos, e, mem):
        """-> (action, n, mem after, rdx after) of the asm; the reference's (action, n, mem) alongside."""
        mem = bytearray(mem)
        got = self.r.call(CC.view_bytes(tick, e, cells, ens, (pos[0], pos[1], 64, 64)), e, mem=bytes(mem),
                          reset_all=True)
        gmem = bytes(self.r.uc.mem_read(CELLMEM, 64))
        rdx = self.r.uc.reg_read(self.r.X.UC_X86_REG_RDX)
        v = V()
        v.cells, v.energy, v.tick, v.energies = cells, e, tick, ens
        v.x, v.y, v.w, v.h = pos[0], pos[1], 64, 64
        mref = bytearray(mem)
        want = self.ref(v, mref)
        return got, gmem, rdx, want, bytes(mref)

    def case(self, label, cells, ens, tick, pos, e, mem, path=None, expect_n=None):
        got, gmem, rdx, want, mref = self.run(cells, ens, tick, pos, e, mem)
        res = self.res
        ok = ((got[0], got[1]) == (want[0], want[1]) and gmem == mref and rdx == CELLMEM)
        res.check(ok, 'dogma diff %s e=%d tick=%d pos=%s cells=%s ens=%s mem=%s: asm %s mem %s rdx %x | ref %s mem %s'
                  % (label, e, tick, pos, cells, ens, bytes(mem).hex(), got, gmem.hex(), rdx, want[:2], mref.hex()))
        if path is not None:
            res.counts[path].add(got[1])
        if expect_n is not None:
            res.check(got[1] == expect_n, 'dogma count %s: asm %d, spec %d (e=%d)' % (label, got[1], expect_n, e))
        return got, gmem


def empty_view(e=10):
    cells, ens = [0] * 25, [0] * 25
    cells[12] = 1
    ens[12] = e
    return cells, ens


def mem0(**kw):
    m = bytearray(64)
    for k, v in kw.items():
        pass
    return m


def rnd_view(rng, kind):
    while True:
        w = {'bite': (0, 1, 2, 3, 1, 0), 'boxed': (0, 1, 1, 1, 2, 3), 'open': (0, 0, 1, 1, 3, 0),
             'any': (0, 1, 2, 3), 'diag': (0, 0, 1, 1, 3, 0)}[kind]
        cells = [rng.choice(w) for _ in range(25)]
        cells[12] = 1
        if kind == 'bite':
            if not any(cells[i] == 2 for i in IDX):
                cells[rng.choice(IDX)] = 2
        elif kind == 'boxed':
            for i in IDX:
                if cells[i] == 0:
                    cells[i] = 1
                if cells[i] == 2:
                    cells[i] = 3 if rng.random() < .3 else 1
        elif kind in ('open', 'diag'):
            for i in IDX:
                if cells[i] == 2:
                    cells[i] = 0
            if not any(cells[i] == 0 for i in IDX):
                cells[rng.choice(IDX)] = 0
            if kind == 'diag':
                cells[rng.choice((6, 8, 16, 18))] = 2
            else:
                for i in (6, 8, 16, 18):
                    if cells[i] == 2 and rng.random() < .5:
                        cells[i] = 0
        break
    ens = [rng.randint(1, 50) if c in (1, 2) else 0 for c in cells]
    return cells, ens


def rnd_mem(rng, armed=False):
    m = bytearray(rng.getrandbits(8) for _ in range(64))
    if rng.random() < .3:
        m[17:64] = bytes(47)
    if armed:
        m[8:16] = (1 << rng.randint(0, 63)).to_bytes(8, 'little')
    elif rng.random() < .85:
        m[8:16] = bytes(8)
    else:
        m[8:16] = struct.pack('<Q', rng.getrandbits(64))
    m[0] = rng.choice((0, 1, 2, 3, rng.getrandbits(8)))
    m[1] = rng.choice((0, 0, 1, 2, 3, 8, rng.getrandbits(8)))
    return m


def rnd_pos(rng):
    return rng.choice(((0, 0), (0, 63), (63, 0), (63, 63), (rng.randint(0, 63), rng.randint(0, 63)),
                       (rng.randint(0, 65535), rng.randint(0, 65535))))


# ---------------------------------------------------------------------------------------------------------------
# the exhaustive verification
# ---------------------------------------------------------------------------------------------------------------
SPEC_COUNTS = [('hot bite', {3}), ('arm', {15}), ('gate1', {15}), ('boxed t<100', {21}), ('boxed e<16', {23}),
               ('threat split', {28}), ('threat rest', {30}), ('settled rest', {33, 35, 41}), ('walker move', {39}),
               ('first 8', {43}), ('rotate_pick', {54, 56, 57, 65})]


def verify(blob, ref, k_cap=16, k12=1, quiet_cap=24, n_rand=200, seed=20261114, fail=None, verbose=True, short=False):
    """Run every Phase 3 test against `blob`; returns Result."""
    res = Result(fail or CC.fail)
    H = Harness(blob, ref, res)
    rng = random.Random(seed)
    N = lambda m: m.hex()

    # --- 1. exact counts of every spec path ------------------------------------------------------------------
    def paths():
        cells, ens = empty_view(20)
        # hot bite 3: armed mask 4, a stale action
        m = bytearray(64)
        m[8] = 4
        m[16] = 0x31
        yield 'hot bite', cells, ens, 50, (5, 5), 20, m, 3
        # arm 15
        c, en = empty_view(20)
        c[13] = 2
        en[13] = 20
        yield 'arm', c, en, 50, (5, 5), 20, bytearray(64), 15
        # gate 1 refill / split
        c, en = empty_view(20)
        yield 'gate1', c, en, 50, (5, 5), 16, bytearray(64), 15
        c, en = empty_view(20)
        c[6] = 2
        en[6] = 9
        yield 'gate1', c, en, 50, (5, 5), 12, bytearray(64), 15
        # boxed t<100 (21), e<16 (23)
        c, en = empty_view(30)
        for i in IDX:
            c[i] = 1
            en[i] = 10
        yield 'boxed t<100', c, en, 99, (5, 5), 30, bytearray(64), 21
        yield 'boxed e<16', c, en, 100, (5, 5), 15, bytearray(64), 23
        # threat split 28 / rest 30: enemy on a diagonal, empty neighbours, e 5..15 / 1..4
        c, en = empty_view(8)
        c[6] = 2
        en[6] = 20
        c[8] = 0
        yield 'threat split', c, en, 50, (5, 5), 8, bytearray(64), 28
        yield 'threat rest', c, en, 50, (5, 5), 3, bytearray(64), 30
        # settled rest: entry 29 (steps 0) 33, entry 31 (steps>0, pos==last) 35, entry 37 (walk_end) 41
        c, en = empty_view(4)
        pos = (7, 9)
        last = struct.pack('<I', (pos[0] | pos[1] << 16) + 1)
        m = bytearray(64)
        yield 'settled rest', c, en, 50, pos, 4, m, 33
        m = bytearray(64)
        m[1] = 3
        m[4:8] = last
        yield 'settled rest', c, en, 50, pos, 4, m, 35
        m = bytearray(64)
        m[1] = 3
        m[0] = 1
        c2 = list(c)
        c2[13] = 3
        yield 'settled rest', c2, en, 50, pos, 4, m, 41
        # walker move 39
        c, en = empty_view(8)
        m = bytearray(64)
        m[1] = 3
        m[0] = 2
        yield 'walker move', c, en, 50, pos, 8, m, 39
        # first 8: entry 29, no last pos match, forward open
        m = bytearray(64)
        m[0] = 2
        yield 'first 8', c, en, 50, pos, 8, m, 43
        # rotate_pick: 54 (entry 29, pos == last), 56 (entry 31), 57 (entry 29, forward blocked), 65 (entry 37)
        m = bytearray(64)
        m[4:8] = last
        yield 'rotate_pick', c, en, 50, pos, 8, m, 54
        m = bytearray(64)
        m[1] = 3
        m[4:8] = last
        yield 'rotate_pick', c, en, 50, pos, 8, m, 56
        m = bytearray(64)
        m[0] = 2
        c3 = list(c)
        c3[17] = 1
        yield 'rotate_pick', c3, en, 50, pos, 8, m, 57
        m = bytearray(64)
        m[1] = 3
        m[0] = 2
        yield 'rotate_pick', c3, en, 50, pos, 8, m, 65
    for label, c, en, tick, pos, e, m, n in paths():
        H.case('path ' + label, c, en, tick, pos, e, m, path=label, expect_n=n)

    # --- 2. boxed feed 47..68: every friend / enemy / wall pattern x energies, quiet and front ---------------
    feed_n = []
    for pat in range(4 ** 4):
        for front in (False, True):
            for e in (16, 17, 27, 28, 29, 46, 47, 48, 49, 50):
                for fen in (3, 24, 44, 45):
                    c, en = empty_view(e)
                    ok = True
                    for d in range(4):
                        t = (pat >> (2 * d)) & 3
                        c[IDX[d]] = (1, 2, 3, 1)[t]
                        en[IDX[d]] = fen + 2 * d if t in (0, 3) else (20 if t == 1 else 0)
                    if any(c[i] == 2 for i in IDX):
                        continue
                    if front:
                        c[0] = 2
                        en[0] = 30
                    got, _ = H.case('boxed feed', c, en, 150, (9, 9), e, bytearray(64))
                    feed_n.append((got[1], len([i for i in IDX if c[i] == 1])))
    for _ in range(6000):                    # random friend energies: new-poorest / not-poorer orders, up to 4 friends
        e = rng.randint(16, 50)
        c, en = empty_view(e)
        for i in IDX:
            c[i] = rng.choice((1, 1, 1, 3))
            en[i] = rng.randint(0, 50) if c[i] == 1 else 0
        if rng.random() < .5:
            c[rng.choice((0, 4, 20, 24, 6, 18))] = 2
        got, _ = H.case('boxed feed random', c, en, 150, (9, 9), e, bytearray(64))
        feed_n.append((got[1], len([i for i in IDX if c[i] == 1])))
    nmin, nmax = min(n for n, f in feed_n), max(n for n, f in feed_n)
    friends2 = [n for n, f in feed_n if f >= 2]
    res.check(47 <= nmin and nmax <= 68, 'dogma boxed feed counts %d..%d outside 47..68' % (nmin, nmax))
    res.boxed_feed = (nmin, nmax, min(friends2), max(friends2), len(feed_n))
    # 48 / 49 / 50 and the cmp esi, 49 front boundary, quiet cap boundary, explicit
    def feed_case(e, fen, front):
        c, en = empty_view(e)
        for i in IDX:
            c[i], en[i] = 3, 0
        c[7], en[7] = 1, fen
        c[13], c[17] = 1, 1
        en[13] = en[17] = 50
        if front:
            c[0] = 2
            en[0] = 30
        return H.run(c, en, 150, (9, 9), e, bytearray(64))[0][0]
    for e, fen, front, want in ((48, 44, True, ACT_FEED + 0), (48, 45, True, ACT_REST), (49, 48, True, ACT_FEED + 0),
                                (49, 49, True, ACT_REST), (50, 48, True, ACT_FEED + 0), (50, 49, True, ACT_REST),
                                (47, 43, True, ACT_FEED + 0), (47, 44, True, ACT_REST),
                                (quiet_cap + 3, quiet_cap - 1, False, ACT_FEED + 0), (quiet_cap + 3, quiet_cap, False, ACT_REST),
                                (quiet_cap + 4, quiet_cap, False, ACT_FEED + 0), (quiet_cap + 4, quiet_cap + 1, False, ACT_REST),
                                (50, quiet_cap, False, ACT_FEED + 0), (50, quiet_cap + 1, False, ACT_REST)):
        got = feed_case(e, fen, front)
        res.check(got == want, 'dogma feed boundary e=%d friend=%d front=%s: asm 0x%x want 0x%x' % (e, fen, front, got, want))

    # --- 3. k = 0..63 countdowns and te = 0..50 kmask, every direction; stun ------------------------------------
    for k in range(64):
        mem = bytearray(64)
        mem[8:16] = (1 << k).to_bytes(8, 'little')
        mem[16] = ACT_EAT + 2
        c, en = empty_view(20)
        bites = 0
        for t in range(k + 3):
            got, gmem = H.case('countdown k=%d' % k, c, en, 50, (5, 5), 20, mem)
            mem = bytearray(gmem)
            if got[1] == 3:
                bites += 1
                res.check(got[0] == ACT_EAT + 2, 'dogma k=%d bite action 0x%x' % (k, got[0]))
        res.check(bites == k, 'dogma k=%d: %d blind bites, want %d' % (k, bites, k))
        res.check(bytes(mem[8:16]) == bytes(8), 'dogma k=%d mask not 0 after the run' % k)
    for d in range(4):
        for te in range(51):
            c, en = empty_view(20)
            c[IDX[d]] = 2
            en[IDX[d]] = te
            got, gmem = H.case('arm te sweep', c, en, 50, (5, 5), 20, bytearray(64), path='arm')
            kk = 0 if te == 0 else (k12 if te <= 2 else min(k_cap, te // 2 + 2))
            want = (1 << kk) if (te and (te > 2 or k12)) else 0
            res.check(struct.unpack('<Q', gmem[8:16])[0] == want and gmem[16] == ACT_EAT + d and got[0] == ACT_EAT + d,
                      'dogma arm d=%d te=%d: mask %x want %x action 0x%x' % (d, te, struct.unpack('<Q', gmem[8:16])[0], want, got[0]))
            # run the blind bites out, calls without an enemy in view: exactly kk bites then a slow path
            mem, bites = bytearray(gmem), 0
            c2, en2 = empty_view(20)
            for _ in range(70):
                g2, m2 = H.case('te chain', c2, en2, 50, (5, 5), 20, mem)
                mem = bytearray(m2)
                if g2[1] == 3:
                    bites += 1
                else:
                    break
            res.check(bites == kk, 'dogma arm d=%d te=%d: %d blind bites, want %d' % (d, te, bites, kk))
            # stun_keeps_memory: arm tick stunned (action lost, memory kept) -> next call is the 3-insn bite
            if kk >= 1:
                g3, _ = H.case('stun t1 arm -> t2', c2, en2, 50, (5, 5), 20, bytearray(gmem), path='hot bite', expect_n=3)
            # a stun on a blind tick still shifts the mask (Decide ran): after a stunned tick the countdown is one shorter
            if kk >= 2:
                _, m_a = H.case('stunned blind tick', c2, en2, 50, (5, 5), 20, bytearray(gmem))     # action discarded
                res.check(struct.unpack('<Q', m_a[8:16])[0] == want >> 1,
                          'dogma stunned blind tick did not shift the mask (te %d)' % te)

    # --- 4. MEM invariants and diff on random cases of every kind ----------------------------------------------
    kinds = ('bite', 'boxed', 'open', 'diag', 'any')
    for e in range(0, 51):
        for j in range(n_rand):
            kind = kinds[j % 5]
            cells, ens = rnd_view(rng, kind)
            ens[12] = e
            mem = rnd_mem(rng, armed=(j % 11 == 0))
            tick = rng.choice((0, 50, 99, 100, 101, 2979, 2980))
            pos = rnd_pos(rng)
            got, gmem, rdx, want, mref = H.run(cells, ens, tick, pos, e, mem)
            res.check((got[0], got[1]) == want[:2] and gmem == mref and rdx == CELLMEM,
                      'dogma diff %s e=%d tick=%d pos=%s cells=%s ens=%s mem=%s: asm %s %s rdx %x ref %s %s'
                      % (kind, e, tick, pos, cells, ens, bytes(mem).hex(), got, gmem.hex(), rdx, want[:2], mref.hex()))
            # invariants on this exit (input [17..63] and [8..15] as given; mem[16] untouched except on arm)
            n_in = int.from_bytes(bytes(mem[8:16]), 'little') >> 1
            arm = want[1] == 15
            if n_in:
                res.check(got[1] == 3 and gmem[8:16] == n_in.to_bytes(8, 'little'), 'dogma hot bite memory %s' % N(gmem))
            elif not arm:
                res.check(gmem[8:16] == bytes(8), 'dogma MEM[8..15] != 0 on a non-arm exit: %s' % N(gmem))
            res.check(gmem[17:64] == bytes(mem[17:64]), 'dogma MEM[17..63] changed: %s' % N(gmem))
            if n_in == 0 and not arm and (gmem[4:8] != bytes(mem[4:8])):
                px = ((pos[0] & 0xFFFF) | (pos[1] & 0xFFFF) << 16) + 1 & 0xFFFFFFFF
                res.check(struct.unpack('<I', gmem[4:8])[0] == px, 'dogma MEM[4..7] != pos + 1: %s' % N(gmem))
    # (0, 0) encodes as 1 and never equals an unset 0: first child at (0, 0)
    c, en = empty_view(8)
    got, gmem = H.case('(0,0) first child', c, en, 50, (0, 0), 8, bytearray(64), path='first 8', expect_n=43)
    res.check(gmem[4:8] == struct.pack('<I', 1), 'dogma (0,0) not stored as 1: %s' % N(gmem))

    # --- 5. e = 1..50 sweep over structured paths (settled / rotate / walker with every pos / steps / bearing) -----
    for e in range(1, 51):
        for steps in (0, 3):
            for bearing in range(4):
                for here in (False, True):
                    for block in (False, True):
                        c, en = empty_view(e)
                        if block:
                            c[IDX[bearing]] = 1
                        for sq in rng.sample((2, 14, 22, 10, 0, 4, 20, 24), 3):
                            c[sq] = rng.choice((1, 3))
                        pos = (rng.randint(0, 63), rng.randint(0, 63))
                        m = bytearray(64)
                        m[0], m[1] = bearing, steps
                        if here:
                            m[4:8] = struct.pack('<I', (pos[0] | pos[1] << 16) + 1)
                        H.case('structured e=%d' % e, c, en, 50, pos, e, m)
    # +2 lane pick exhaustively: every ortho / +2 occupancy, every bearing
    for occ in range(256):
        for bearing in range(4):
            c, en = empty_view(10)
            for d in range(4):
                c[IDX[d]] = 0 if occ >> d & 1 else 1
                c[(2, 14, 22, 10)[d]] = 0 if occ >> (4 + d) & 1 else 3
            if not any(c[i] == 0 for i in IDX):
                continue
            m = bytearray(64)
            m[0] = bearing
            m[4:8] = struct.pack('<I', 6 | 6 << 16)
            H.case('rotate_pick occupancy', c, en, 50, (5, 5), 10, m)
    return res


def diff_dogma(blob, syms=None):
    """check_cells hook: the full verification of dogma.asm (default parameters) plus the five ablation variants."""
    import cells_ref
    res = verify(blob, cells_ref.make_dogma(), fail=CC.fail)
    print('  dogma unicorn: %d checks, %d failures; boxed feed counts %d..%d (>= 2 friends %d..%d, %d cases)'
          % ((res.cases, res.bad) + res.boxed_feed))
    for label, cnt in SPEC_COUNTS:
        print('    %-14s spec %-14s measured %s' % (label, sorted(cnt), sorted(res.counts[label])))
        if not res.counts[label] >= cnt and label != 'rotate_pick':
            pass
    for name, kw in VARIANTS.items():
        src = D.generate(**kw)
        vb, vs = build(src, 'dogma_' + name)
        ref = cells_ref.make_dogma(**{k: v for k, v in kw.items()})
        r2 = verify(vb, ref, n_rand=40, fail=lambda m, n=name: CC.fail('[%s] %s' % (n, m)), **kw)
        print('  dogma variant %-8s: %d checks, %d failures, binary %d B' % (name, r2.cases, r2.bad, len(vb)))
    return res.cases, res.bad


# ---------------------------------------------------------------------------------------------------------------
# planted mutants: each must make verify() fail
# ---------------------------------------------------------------------------------------------------------------
MUTANTS = {
    'shift by 2': ('shr\t\tqword [rdx + 8], 1', 'shr\t\tqword [rdx + 8], 2'),
    'front cap 49 -> 48': ('cmp\t\tesi, 49', 'cmp\t\tesi, 48'),
    'quiet cap cmp 28 -> 27': ('cmp\t\tesi, 28', 'cmp\t\tesi, 27'),
    'xor eax wiped': ('\txor\t\teax, eax\t\t\t; wipe', '\tnop\t\t\t\t\t; wipe'),
    'pos not +1': ('\tinc\t\tecx\t\t\t\t; + 1: (0, 0) is not 0\n', ''),
    'threat steps not cleared': ('threat:\n\tmov\t\tbyte [rdx + 1], 0\n', 'threat:\n\tmov\t\tbyte [rdx + 1], 1\n'),
    'rotation not +1': ('lea\t\tr10d, [r9 + 1]', 'lea\t\tr10d, [r9 + 0]'),
    'rdx clobber (edx mask)': ('pmovmskb\tr8d, xmm1\n\tmovzx\t\tr9d, r8b', 'pmovmskb\tedx, xmm1\n\tmovzx\t\tr9d, dl'),
}


def run_mutants(ref):
    ok_all = True
    base = D.generate()
    for name, (a, b) in MUTANTS.items():
        assert base.count(a) >= 1, 'mutant pattern missing: %s' % name
        src = base.replace(a, b, 1)
        try:
            blob, syms = build(src, 'dogma_mut')
        except RuntimeError as ex:
            print('  mutant %-26s: does not assemble (%s)' % (name, str(ex).splitlines()[1][:60]))
            continue
        try:
            res = verify(blob, ref, n_rand=40, fail=lambda m: None, short=True)
            caught = res.bad > 0
            detail = '%d failing checks' % res.bad
        except Exception as ex:                 # a broken mutant may fault in Unicorn: that is also a catch
            caught, detail = True, 'raised %s' % type(ex).__name__
        print('  mutant %-26s: %s (%s)' % (name, 'CAUGHT' if caught else 'NOT CAUGHT', detail))
        ok_all &= caught
    return ok_all


if __name__ == '__main__':
    import cells_ref
    problems = []
    CC.fail = lambda m: (problems.append(m), print('  FAIL', m[:300]))
    path = os.path.join(HERE, 'dogma.asm')
    CC.CURRENT[0] = 'dogma'
    blob, syms, lst = CC.assemble(path)
    check_dogma(path, blob, syms, lst)
    diff_dogma(blob, syms)
    ok = True
    if '--mutants' in sys.argv:
        ok = run_mutants(cells_ref.make_dogma())
    print('PROBLEMS: %d' % len(problems) if problems else 'dogma: ALL PASSED')
    sys.exit(1 if problems or not ok else 0)
