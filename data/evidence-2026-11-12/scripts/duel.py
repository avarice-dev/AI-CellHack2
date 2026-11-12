"""Scratch: bite duels between two enemy cells that are edge neighbours at the start of tick t and both alive.
'armed' = the cell bit THIS opponent on tick t-1 (its repeat path for that square is ready).  Per tick and pair,
outcome = which of the two bit the other first this tick (first EAT event between them in event order), or neither.
Rows per (colony X, colony Y) with X < Y by colony index, split by (X armed, Y armed):  X first / Y first / neither.
A cell's repeat path beats the other's when it wins while both are armed; a stun lock shows as one side never
armed.  Usage: python duel.py <replay dir> <names.json> <out.csv> [id ...]
"""
import collections
import csv
import gzip
import json
import os
import struct
import sys

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def run(path):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf = {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    out = collections.Counter()
    prev_bites = set()               # (eater, target) on the previous tick

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
                    ids.append(cid); colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                loaded = True
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 4 + 8
            nev = U32.unpack_from(raw, p)[0]; p += 4
            snap = grid
            pairs = set()
            for cid in ids:
                c = colOf[cid]
                for s in nbrs(sqOf[cid]):
                    g = snap[s]
                    if g and colOf[g - 1] != c and cid < g - 1:
                        pairs.add((cid, g - 1))
            grid = snap[:]
            first = {}
            bites = set()
            births, dead = [], set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if k == 4 and colOf[a] != colOf[b]:
                        bites.add((a, b))
                        key = (min(a, b), max(a, b))
                        first.setdefault(key, a)
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                    births.append(cid)
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            w = 'a' if t < 100 else 'b'
            for a, b in pairs:
                ca, cb = colOf[a], colOf[b]
                if ca > cb:
                    a, b, ca, cb = b, a, cb, ca
                arm_a, arm_b = (a, b) in prev_bites, (b, a) in prev_bites
                f = first.get((min(a, b), max(a, b)))
                res = 'x' if f == a else 'y' if f == b else 'n'
                out[(ca, cb, w, int(arm_a), int(arm_b), res)] += 1
            prev_bites = bites
            n = U32.unpack_from(raw, p)[0]; p += 4 + n
            for cid in dead:
                s = sqOf.pop(cid, None)
                if s is not None and grid[s] == cid + 1:
                    grid[s] = 0
            ids = [i for i in ids if i not in dead] + [b for b in births if b not in dead]
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
        nmf = lambda c: nm[c] if c < len(nm) else 'colony %d' % c
        for (ca, cb, w, xa, ya, res), n in out.items():
            rows.append(dict(replay=rid, x=nmf(ca), y=nmf(cb), window=w, x_armed=xa, y_armed=ya, result=res, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'x', 'y', 'window', 'x_armed', 'y_armed', 'result', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
