"""Scratch: chains of our Bane v2.1/v2.2 bites for blind-queue sizing (real replays, no models).
Chain start = our cell eats an enemy T it did not eat on the previous tick.  Recorded: T's energy at that tick's start
(e0, what our cell sees), our other cells adjacent to T (nf, capped 3), T's own friends adjacent to T (ntf, possible
feeders, capped 3), and the horizon H = number of later ticks T is still alive on the same square at tick start
(capped 12), with how it ended (died / gone = moved or cap).  A queue armed at the chain start with k blind bites hits
min(k, H) times and bites an empty or refilled square max(0, k - H) times (first-order: T's real survival).
Usage: python queue_chains.py <replay dir> <names.json> <out.csv> [id ...]
"""
import collections
import csv
import gzip
import json
import os
import struct
import sys

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))
BANE = {'Bane', 'Bane v2', 'Bane v2.1', 'Bane v2.2', 'Bane L', 'Bane W'}


def era(rid):
    return 'v1' if rid < 124690 else 'v2.0' if rid < 126000 else 'v2.1' if rid < 127810 else 'v2.2'



def choose(E):
    """Bane's bite_tbl choice (gen_covetous / gen_sprint fight table): one enemy -> it; two or four -> first of DOWN,
    LEFT, UP, RIGHT; three -> the one opposite the single non-enemy side.  Directions 0 UP 1 RIGHT 2 DOWN 3 LEFT."""
    if len(E) == 3:
        m = ({0, 1, 2, 3} - set(E)).pop()
        return (m + 2) % 4
    for d in (2, 3, 0, 1):
        if d in E:
            return d


def cls(lo, hi):
    if hi == 4 and lo < 4:
        return '<4'
    if lo == 4 and hi == 4:
        return '=4'
    if lo == 4 and hi == 16:
        return '5-15'
    if lo == 16 and hi == 16:
        return '=16'
    if lo >= 16:
        return '>16'
    return 'other'


def run(path, own, bane):
    """own: colony -> 'v1' / 'v2.0' / 'v2.1' / 'v2.2' (a Bane) or 'conv' (Conviction: split e >= 16 = 14)."""
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    out = collections.Counter()
    prev = set()
    lock = {}
    pend = {}
    dead_prev = set()
    SPLIT = {'v1': 11, 'v2.0': 11, 'v2.1': 16, 'v2.2': 16, 'conv': 14}

    def nbrs(s):
        x, y = s % W, s // W
        for dx, dy in DIRS:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                yield (y + dy) * W + x + dx

    while p < n_raw:
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8
            cells = [BIRTH.unpack_from(raw, p + 10 * i) for i in range(n)]; p += 10 * n
            if not loaded:
                for cid, c, x, y, e in cells:
                    ids.append(cid); colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                loaded = True
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 4 + 8
            nev = U32.unpack_from(raw, p)[0]; p += 4
            snap = grid
            sq0 = dict(sqOf)
            grid = snap[:]
            evs = []                      # (kind, actor, target)
            births, dead = [], set()
            acted = set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    evs.append(('eat' if k == 4 else 'feed', a, b))
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    s = y * W + x
                    par = None            # parent: a same-colony edge neighbour at tick start that has not acted,
                    for q in nbrs(s):     # preferring one with floor(E / 2) = the child's energy
                        g = snap[q]
                        if g and colOf.get(g - 1) == c and g - 1 not in acted and g - 1 not in dead:
                            if par is None or enOf.get(g - 1, 0) // 2 == e:
                                par = g - 1
                    colOf[cid] = c; sqOf[cid] = s; grid[s] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    evs.append(('split', par, cid))
                    if par is not None:
                        acted.add(par)
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    evs.append(('move', cid, None))
                    acted.add(cid)
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
                if k in (4, 5):
                    acted.add(a)
            # markers and rival bites in event order
            cost = [None] * len(evs)
            eats = set()
            for i, (kind, a, b) in enumerate(evs):
                if a is None or colOf.get(a) not in own:
                    continue
                oc = colOf[a]
                ver = own[oc]
                if kind == 'eat' and colOf.get(b) != oc:
                    if ver in ('v1', 'v2.0'):
                        cost[i] = 5
                    elif ver in ('v2.1', 'v2.2') and (a, b) in prev:
                        cost[i] = 4
                elif kind == 'split':
                    s = sq0.get(a)
                    if s is None or enOf.get(a, 0) < 16:
                        continue
                    if any(snap[q] and colOf[snap[q] - 1] != oc for q in nbrs(s)):
                        continue
                    cost[i] = SPLIT[ver]
                elif kind == 'move' and ver == 'v2.2':
                    cost[i] = 39
            mk = [c for c in cost if c is not None]
            for j in range(1, len(mk)):
                if mk[j] < mk[j - 1]:
                    out[('_check', 'violation', '')] += 1
            out[('_check', 'markers', '')] += len(mk)
            # prefix max / suffix min of marker costs
            lo, hi = [0] * len(evs), [999] * len(evs)
            m = 0
            for i in range(len(evs)):
                lo[i] = m
                if cost[i] is not None:
                    m = max(m, cost[i])
            m = 999
            for i in range(len(evs) - 1, -1, -1):
                hi[i] = m
                if cost[i] is not None:
                    m = min(m, cost[i])
            DV = {-W: 0, 1: 1, W: 2, -1: 3}
            w = 'a' if t < 100 else 'b'
            # pending chains: T -> list of [t0, e0, nf0, ntf0, rival colony, window, square]
            for T in list(pend):
                keep = []
                for ch in pend[T]:
                    if T in sq0 and sq0[T] == ch[6] and t - ch[0] <= 12:
                        keep.append(ch)
                    else:
                        H = min(t - 1 - ch[0], 12)
                        out[(ch[4], ch[5], ch[1], ch[2], ch[3], H, 'died' if T in dead_prev else 'gone')] += 1
                if keep:
                    pend[T] = keep
                else:
                    del pend[T]
            for i, (kind, a, b) in enumerate(evs):
                if kind != 'eat' or colOf.get(a) != bane or colOf.get(b) == bane or (a, b) in prev:
                    continue
                st = sq0.get(b)
                if st is None:
                    continue
                nf = sum(1 for q in nbrs(st) if snap[q] and colOf[snap[q] - 1] == bane and snap[q] - 1 != a)
                ntf = sum(1 for q in nbrs(st) if snap[q] and colOf[snap[q] - 1] == colOf[b])
                pend.setdefault(b, []).append([t, enOf.get(b, 0), min(nf, 3), min(ntf, 3), colOf[b], w, st])
            eats = set()
            for i, (kind, a, b) in enumerate(evs):
                if kind == 'eat' and colOf.get(a) != colOf.get(b):
                    eats.add((a, b))
                    if colOf.get(a) == bane:
                        lock[a] = DV.get(sq0.get(b, -1) - sq0.get(a, -2))
                elif kind == 'split' and a is not None and colOf.get(a) == bane:
                    lock[b] = lock.get(a)
            prev = eats
            dead_prev = set(dead)
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            for cid in dead:
                s = sqOf.pop(cid, None)
                if s is not None and grid[s] == cid + 1:
                    grid[s] = 0
            ids = [i for i in ids if i not in dead] + [b for b in births if b not in dead]
            for cid, e in zip(ids, en):
                enOf[cid] = e
        elif rt == 3:
            p += 5 + 4 + 8
        else:
            raise ValueError((rt, p))
    return out


if __name__ == '__main__':
    rdir, names_path, outp = sys.argv[1:4]
    want = set(sys.argv[4:])
    names = json.load(open(names_path, encoding='utf-8'))
    rows = []
    for f in sorted(os.listdir(rdir)):
        rid = f.split('.')[0]
        if want and rid not in want:
            continue
        nm = [n[:-2] if n.endswith((' W', ' L')) else n for n in names.get(rid, [])]
        bc = [c for c, n in enumerate(nm) if n in BANE]
        cc = [c for c, n in enumerate(nm) if n == 'Conviction']
        if len(bc) != 1 or len(cc) > 1 or era(int(rid)) not in ('v2.1', 'v2.2'):
            continue
        own = {c: era(int(rid)) for c in bc}
        own.update({c: 'conv' for c in cc})
        out = run(os.path.join(rdir, f), own, bc[0])
        for key, n in out.items():
            if key[0] == '_check':
                rows.append(dict(replay=rid, era=own[bc[0]], rival='_check', window=key[1], e0=key[2], nf='', ntf='',
                                 H='', end='', n=n))
                continue
            c, w, e0, nf, ntf, H, how = key
            rows.append(dict(replay=rid, era=own[bc[0]], rival=nm[c] if c < len(nm) else 'colony %d' % c, window=w,
                             e0=e0, nf=nf, ntf=ntf, H=H, end=how, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'era', 'rival', 'window', 'e0', 'nf', 'ntf', 'H',
                                            'end', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
