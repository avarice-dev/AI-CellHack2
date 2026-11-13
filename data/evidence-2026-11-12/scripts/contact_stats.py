"""Scratch (design v0, request ii): Bane v2.2 front facts from real replays, by window (a t < 30, b < 60, c < 100,
d < 300, e later).  Rows (key, n):
  kill|<rival group>|<boxedfriend6>  enemy cells killed by a Bane bite (the killer = the cell's last enemy biter on its
        death tick, a Bane cell); boxedfriend6 = 1 if the killer had, at the start of that tick, a friend on an edge
        that has no empty edge and energy >= 6
  contact|<enemies on edges 1/2/3/4>|<energy bucket>  Bane cell-ticks with >= 1 enemy on an edge at tick start;
        energy bucket of the Bane cell: <5, 5-15, 16-30, 31-46, 47+
Usage: python contact_stats.py <replay dir> <names.json> <out.csv> [id ...]
"""
import collections
import csv
import gzip
import json
import os
import struct
import sys

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def grp(n):
    return 'Siect-F' if 'Siect' in n else 'Yen' if ('VarSi' in n or 'Cog' in n or 'Clippy' in n) else \
        'feeder' if any(k in n for k in ('Colossus', 'medivac', 'NomNom2')) else 'other'


def ebk(e):
    return '<5' if e < 5 else '5-15' if e < 16 else '16-30' if e < 31 else '31-46' if e < 47 else '47+'


def win(t):
    return 'a' if t < 30 else 'b' if t < 60 else 'c' if t < 100 else 'd' if t < 300 else 'e'


def run(path, bane, names):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded = [], False
    out = collections.Counter()

    def nbrs(s):
        x, y = s % W, s // W
        for dx, dy in DIRS:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                yield (y + dy) * W + x + dx

    while p < len(raw):
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
            w = win(t)
            bf6 = {}
            for cid in ids:
                if colOf[cid] != bane:
                    continue
                s = sqOf[cid]
                ne = sum(1 for q in nbrs(s) if snap[q] and colOf[snap[q] - 1] != bane)
                if ne:
                    out[('contact|%d|%s' % (ne, ebk(enOf.get(cid, 0))), w)] += 1
                ok = 0
                for q in nbrs(s):
                    g = snap[q]
                    if g and colOf[g - 1] == bane and enOf.get(g - 1, 0) >= 6 and \
                            all(snap[r] for r in nbrs(q)):
                        ok = 1
                        break
                bf6[cid] = ok
            grid = snap[:]
            births, dead = [], set()
            last_biter = {}
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if k == 4 and colOf.get(a) != colOf.get(b):
                        last_biter[b] = a
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                    births.append(cid)
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                elif k == 3:
                    dead.add(U32.unpack_from(raw, p + 1)[0]); p += 5
                else:
                    raise ValueError(k)
            for cid in dead:
                a = last_biter.get(cid)
                if a is not None and colOf.get(a) == bane and colOf.get(cid) != bane:
                    out[('kill|%s|%d' % (grp(names[colOf[cid]] if colOf[cid] < len(names) else ''), bf6.get(a, 0)), w)] += 1
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
        bc = [c for c, n in enumerate(nm) if n == 'Bane v2.2']
        if len(bc) != 1 or int(rid) < 127810:
            continue
        for (key, w), n in run(os.path.join(rdir, f), bc[0], nm).items():
            rows.append(dict(replay=rid, key=key, window=w, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'key', 'window', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
