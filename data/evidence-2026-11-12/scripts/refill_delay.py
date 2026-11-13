"""Scratch (review Track B, first measure): refill delay after an enemy kills one of our Bane v2.2 cells.
For every square freed by an enemy bite on a Bane cell (killer = the cell's last enemy biter on its death tick), the
first birth into that square: delay = birth tick - death tick - 1 (0 = refilled on the next tick), or 'taken' (another
colony entered it first, by birth or move) / 'none' (still empty after 12 ticks).  For our refills: was the child
bitten on its first live tick (birth tick + 1) by any enemy, by the killer; the killer's state at the refill (alive and
still on an edge of the square: 0/1); child dead within 5 ticks.
Rows: replay, killer colony (name), window (a t < 100, b < 300, c later), delay (0, 1, 2, 3+, taken, none), killer
adjacent at the refill (0/1/-), bitten1 any, bitten1 by killer, dead5, n.
Usage: python refill_delay.py <replay dir> <names.json> <out.csv> [id ...]
"""
import collections
import csv
import gzip
import json
import os
import struct
import sys

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))
MAXD = 12


def run(path, bane):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf = {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    out = collections.Counter()
    freed = {}                       # square -> (death tick, killer id)
    child = {}                       # our refill child id -> [birth tick, killer, delay key, adj, bitten any, by killer]
    died_at = {}

    def nbrs(s):
        x, y = s % W, s // W
        for dx, dy in DIRS:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                yield (y + dy) * W + x + dx

    def win(t):
        return 'a' if t < 100 else 'b' if t < 300 else 'c'

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
            grid = snap[:]
            births, dead = [], set()
            last_biter = {}
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if k == 4 and colOf.get(a) != colOf.get(b):
                        last_biter[b] = a
                        if b in child and t == child[b][0] + 1:
                            child[b][4] = 1
                            if a == child[b][1]:
                                child[b][5] = 1
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    s = y * W + x
                    colOf[cid] = c; sqOf[cid] = s; grid[s] = cid + 1
                    births.append(cid)
                    f = freed.pop(s, None)
                    if f is not None:
                        td, kil = f
                        kc = colOf[kil]
                        if c == bane:
                            d = t - td - 1
                            dk = str(d) if d < 3 else '3+'
                            ks = sqOf.get(kil)
                            adj = int(kil not in died_at and ks is not None and ks in set(nbrs(s)))
                            child[cid] = [t, kil, (kc, win(td), dk, adj), adj, 0, 0]
                        else:
                            out[(kc, win(td), 'taken', '-', '-', '-', '-')] += 1
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    s = y * W + x
                    grid[s] = cid + 1; sqOf[cid] = s
                    f = freed.pop(s, None)
                    if f is not None:
                        out[(colOf[f[1]], win(f[0]), 'taken', '-', '-', '-', '-')] += 1
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            for cid in dead:
                died_at[cid] = t
                a = last_biter.get(cid)
                if colOf.get(cid) == bane and a is not None and colOf.get(a) != bane and cid in sqOf:
                    freed[sqOf[cid]] = (t, a)
            for s in [s for s, (td, _) in freed.items() if t - td > MAXD]:
                td, kil = freed.pop(s)
                out[(colOf[kil], win(td), 'none', '-', '-', '-', '-')] += 1
            for cid in list(child):
                tb, kil, key, adj, b1, bk = child[cid]
                if cid in dead or t - tb >= 5:
                    out[key + (b1, bk, int(cid in dead and t - tb <= 5))] += 1
                    del child[cid]
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


COLS = ['replay', 'killer', 'window', 'delay', 'killer_adj', 'bitten1', 'bitten1_killer', 'dead5', 'n']

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
        bc = [c for c, n in enumerate(nm) if n == 'Bane v2.2']
        if len(bc) != 1 or int(rid) < 127810:
            continue
        out = run(os.path.join(rdir, f), bc[0])
        for key, n in out.items():
            rows.append(dict(zip(COLS, [rid, nm[key[0]] if key[0] < len(nm) else 'colony %d' % key[0]] + list(key[1:]) + [n])))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=COLS)
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
