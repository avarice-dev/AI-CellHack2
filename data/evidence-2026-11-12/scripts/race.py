"""Scratch: races between our Bane v2.1/v2.2 cells and adjacent enemies, from real replays (no models).
Our stored bite is reconstructed: it is the direction of the cell's last bite (kept through stuns, copied to a child
from its parent).  At tick start each of our cells with an adjacent enemy has a plan: 'lock' (stored direction holds
an enemy: bite it, 4 instructions) or 'first' (bite_tbl's choice, 16).  Outcome: 'A' = our cell bit its planned
target before anything bit it; 'B' = an enemy bit our cell before it acted (the cell is stunned).  For 'B', the
enemy's bite cost class comes from the event-order markers (see order.py) and its direction is from the enemy's view.
Plan 'lock-other' / 'first-other' = our cell meant to bite someone else.  Checks: our eats go the planned direction.
Column newborn (review measure 7): 1 = the race is on our cell's first live tick (born on the tick before; its
stored bite is the one copied from its parent).  Split parents: energy-matched (parents.py) since 2026-11-13.
Usage: python race.py <replay dir> <names.json> <out.csv> [id ...]
"""
import collections
import csv
import gzip
import json
import os
import struct
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))   # append: keep the stdlib ahead of scratch modules
import parents  # noqa: E402

RUN = parents.Running()
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
    born_at = {}
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
            RUN.tick(enOf)
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
                    RUN.event(k, a, b)
                    evs.append(('eat' if k == 4 else 'feed', a, b))
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    s = y * W + x
                    cnd = [g - 1 for g in (snap[q] for q in nbrs(s))
                           if g and colOf.get(g - 1) == c and g - 1 not in acted and g - 1 not in dead]
                    par, _tag = RUN.parent(cnd, e)   # energy-matched parent (parents.py); None if unknown
                    born_at[cid] = t
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
            first_bitten, own_act = {}, {}
            for i, (kind, a, b) in enumerate(evs):
                if a is not None and a not in own_act:
                    own_act[a] = i
                if kind == 'eat' and colOf.get(a) != colOf.get(b) and b not in first_bitten:
                    first_bitten[b] = (i, a)
            w = 'a' if t < 100 else 'b'
            for A in ids:
                if colOf.get(A) != bane or A not in sq0:
                    continue
                s = sq0[A]
                E = {}
                for q in nbrs(s):
                    g = snap[q]
                    if g and colOf[g - 1] != bane:
                        E[DV[q - s]] = g - 1
                if not E:
                    continue
                L = lock.get(A)
                if L is not None and L in E:
                    plan, d = 'lock', L
                else:
                    plan, d = 'first', choose(E)
                T = E[d]
                fb = first_bitten.get(A)
                ai = own_act.get(A)
                if ai is not None and (fb is None or ai < fb[0]):
                    kind, a, b = evs[ai]
                    if kind == 'eat' and colOf.get(b) != bane:
                        dd = DV.get(sq0.get(b, -1) - s)
                        out[('_check', 'eat_dir_ok' if dd == d else 'eat_dir_bad', plan)] += 1
                        if b == T:
                            out[(colOf[T], 'UR DL'[0] if False else 'URDL'[(d + 2) % 4], plan, (A, T) in prev,
                                 (T, A) in prev, 'A', '-', w, int(born_at.get(A) == t - 1))] += 1
                    else:
                        out[('_check', 'acted_not_eat', kind)] += 1
                elif fb is not None:
                    i, B = fb
                    sb = sq0.get(B)
                    dab = DV.get(sb - s) if sb is not None else None
                    if dab is None:
                        continue
                    c = cls(lo[i], hi[i])
                    out[(colOf[B], 'URDL'[(dab + 2) % 4], plan if B == T else plan + '-other', (A, B) in prev,
                         (B, A) in prev, 'B', c, w, int(born_at.get(A) == t - 1))] += 1
            eats = set()
            for i, (kind, a, b) in enumerate(evs):
                if kind == 'eat' and colOf.get(a) != colOf.get(b):
                    eats.add((a, b))
                    if colOf.get(a) == bane:
                        lock[a] = DV.get(sq0.get(b, -1) - sq0.get(a, -2))
                elif kind == 'split' and a is not None and colOf.get(a) == bane:
                    lock[b] = lock.get(a)
            prev = eats
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
                rows.append(dict(replay=rid, era=own[bc[0]], rival='_check', rdir=key[1], plan=key[2], a_armed='',
                                 b_armed='', first='', bcost='', window='', newborn='', n=n))
                continue
            c, rd, plan, aa, ba, fi, bcost, w, nb = key
            rows.append(dict(replay=rid, era=own[bc[0]], rival=nm[c] if c < len(nm) else 'colony %d' % c, rdir=rd,
                             plan=plan, a_armed=int(aa), b_armed=int(ba), first=fi, bcost=bcost, window=w, newborn=nb, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'era', 'rival', 'rdir', 'plan', 'a_armed', 'b_armed', 'first',
                                            'bcost', 'window', 'newborn', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
