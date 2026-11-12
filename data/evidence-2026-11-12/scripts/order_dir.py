"""Scratch: bracket rival bite costs between Bane events of known instruction count (real replays, no models).
The engine acts in instruction-count order (fewest first, seeded coin on ties) and the replay logs events in that
order.  Bane events whose count is fixed by what the replay shows:
  v2.1 / v2.2 (ids >= 126000): an eat on the target the same cell ate on the previous tick = stored bite, 4;
      a split by a cell with no adjacent enemy at tick start and energy >= 16 = gate 1, 16;
      v2.2 only (ids >= 127810): a move = walker move, 39.
  v1 / v2.0 (ids < 126000): any eat = 5 (scan-first bite); a split as above (no adjacent enemy, e >= 16) = 11.
Check first: within a tick, markers must appear in non-decreasing cost order (counts violations).
For every eat event by another colony: the largest marker cost before it (lo) and the smallest after it (hi) in the
same tick; its cost c satisfies lo <= c <= hi (ties possible at both ends).  Split by kind: 'repeat' (the eater ate the
same target on the previous tick) or 'first'; and target: a Bane cell or anything else.
Also records the bite direction (U/R/D/L from the eater's square at tick start).
Usage: python order_dir.py <replay dir> <names.json> <out.csv> [id ...]
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


def run(path, own):
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
            for i, (kind, a, b) in enumerate(evs):
                if kind != 'eat':
                    continue
                if colOf.get(a) == colOf.get(b):
                    continue
                eats.add((a, b))
                if colOf.get(a) in own:
                    continue
                rk = 'repeat' if (a, b) in prev else 'first'
                tg = own.get(colOf.get(b), 'other')
                sa, sb = sq0.get(a), sq0.get(b)
                dd = '?' if sa is None or sb is None else {-W: 'U', 1: 'R', W: 'D', -1: 'L'}.get(sb - sa, '?')
                out[(colOf[a], rk, tg, 'a' if t < 100 else 'b', lo[i], hi[i], dd)] += 1
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
        if len(bc) > 1 or len(cc) > 1 or not (bc or cc):
            continue
        own = {c: era(int(rid)) for c in bc}
        own.update({c: 'conv' for c in cc})
        ver = '+'.join(sorted(own.values()))
        out = run(os.path.join(rdir, f), own)
        for key, n in out.items():
            if key[0] == '_check':
                rows.append(dict(replay=rid, era=ver, rival=key[0], kind=key[1], target='', window='', lo='', hi='', dir='',
                                 n=n))
                continue
            c, rk, tg, w, lo, hi, dd = key
            rows.append(dict(replay=rid, era=ver, rival=nm[c] if c < len(nm) else 'colony %d' % c, kind=rk, target=tg,
                             window=w, lo=lo, hi=hi, dir=dd, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'era', 'rival', 'kind', 'target', 'window', 'lo', 'hi', 'dir', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
