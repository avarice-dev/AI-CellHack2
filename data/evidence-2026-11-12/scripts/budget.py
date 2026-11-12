"""Scratch: action budget per colony from real replays (no cell code, no models).
Every live cell-tick is classed by what the cell did and by its situation at the start of the tick:
  act:   split, move, feed, eat, stunned (bitten before its turn), none (no event: rest, hold, or a split/move that
         failed because the square was taken first; failed moves/splits cannot be told apart from rests here)
  space: 'open' = at least one empty edge neighbour, 'boxed' = none
  enemy: 'front' = an enemy on an edge, 'near' = an enemy elsewhere in the 5x5, 'far' = no enemy in the 5x5
  energy bucket: <5, 5-11, 12-15, 16-49, 50 (cap)
Windows: a t0-30, b 30-60, c 60-100, d 100-200, e 200+.
Key derived measure: idle-with-space = none & open & energy >= 5 (could have split), split by enemy situation.
From t300 on, 'near' is not computed (shown as 'far' unless the enemy is on an edge).
Usage: python budget.py <replay dir> <names.json> <out.csv> [id ...]
"""
import collections
import csv
import gzip
import json
import os
import struct
import sys

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))
RING = [(dx, dy) for dy in range(-2, 3) for dx in range(-2, 3) if (dx, dy) != (0, 0)]


def win(t):
    return 'a' if t < 30 else 'b' if t < 60 else 'c' if t < 100 else 'd' if t < 200 else 'e'


def ebk(e):
    return '<5' if e < 5 else '5-11' if e < 12 else '12-15' if e < 16 else '16-49' if e < 50 else '50'


def run(path):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    out = collections.Counter()
    last_w = None

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
            w = win(t)
            snap = grid
            sit = {}
            for cid in ids:
                c = colOf[cid]
                s = sqOf[cid]
                x, y = s % W, s // W
                opn = False
                front = False
                for dx, dy in DIRS:
                    if 0 <= x + dx < W and 0 <= y + dy < H:
                        g = snap[(y + dy) * W + x + dx]
                        if not g:
                            opn = True
                        elif colOf[g - 1] != c:
                            front = True
                near = front
                if not near and t < 300:                    # 5x5 enemy check only before t300 (cost)
                    for dx, dy in RING:
                        if 0 <= x + dx < W and 0 <= y + dy < H:
                            g = snap[(y + dy) * W + x + dx]
                            if g and colOf[g - 1] != c:
                                near = True
                                break
                sit[cid] = ('open' if opn else 'boxed', 'front' if front else 'near' if near else 'far',
                            ebk(enOf.get(cid, 0)))
            grid = snap[:]
            what, births, dead = {}, [], set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if a not in what:
                        what[a] = 'eat' if k == 4 else 'feed'
                    if k == 4 and b not in what:
                        what[b] = 'stunned'
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    xs, ys = x, y
                    for dx, dy in DIRS:
                        if 0 <= xs + dx < W and 0 <= ys + dy < H:
                            g = snap[(ys + dy) * W + xs + dx]
                            if g and colOf[g - 1] == c and (g - 1) not in what:
                                what[g - 1] = 'split'
                                break
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    what.setdefault(cid, 'move')
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            for cid, (sp, en_, eb) in sit.items():
                out[(colOf[cid], w, what.get(cid, 'none'), sp, en_, eb)] += 1
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
        nm = names.get(rid, [])
        out = run(os.path.join(rdir, f))
        for (c, w, act, sp, en_, eb), n in out.items():
            name = nm[c] if c < len(nm) else 'colony %d' % c
            rows.append(dict(replay=rid, colony=c, name=name, window=w, act=act, space=sp, enemy=en_, energy=eb, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'colony', 'name', 'window', 'act', 'space', 'enemy', 'energy', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
