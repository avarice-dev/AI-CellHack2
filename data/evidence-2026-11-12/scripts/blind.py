"""Scratch: two front tests per colony from real replays (no cell code, no models).
(1) Blind or checked repeat bite.  A cell that bit square S on tick t, is not stunned on t+1, finds S EMPTY at the
    start of t+1 and has another enemy on a different edge: what does it do on t+1?  A bite that checks the square
    (or scans) bites the other enemy ('eat'); a blind repeat bite hits the empty square and shows no event ('none').
    Also the same test when S holds a NEW enemy cell (a refill): does the cell bite again ('eat') at once?
(2) Refill into a square freed by an enemy kill: the colony whose cell died puts a new child into the square on the
    next tick ('refill'); is that child bitten on its first live tick by the killer, how much energy do the killer's
    bites take from it over its life, and does it die within 5 ticks?
Usage: python blind.py <replay dir> <names.json> <out.csv> [id ...]
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
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    out = collections.Counter()
    bit_sq = {}                      # eater -> (square it bit, tick)
    bit_tg = {}                      # eater -> target id it bit
    killer_of = {}                   # dead cell -> its last enemy biter
    pend_refill = {}                 # tick -> list of (square, killer id, killer colony, dead colony)
    refills = {}                     # child id -> [killer id, killer colony, tick born, bites by killer, took]
    dead_all = set()

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
            # test (1) candidates at tick start
            cand = {}
            for a, (s, tb) in list(bit_sq.items()):
                if tb != t - 1 or a in dead_all or a not in sqOf:
                    continue
                c = colOf[a]
                g = snap[s]
                others = [snap[q] - 1 for q in nbrs(sqOf[a]) if q != s and snap[q] and colOf[snap[q] - 1] != c]
                if not g and others:
                    b = bit_tg.get(a)
                    why = 'self' if killer_of.get(b) == a else 'other' if b in dead_all else 'moved'
                    cand[a] = 'empty'
                    cand[(a, 'why')] = why
                elif g and colOf[g - 1] != c and g - 1 in refills:
                    cand[a] = 'refill'
            grid = snap[:]
            what, births, dead = {}, [], set()
            last_biter = {}
            new_bites = {}
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if a not in what:
                        what[a] = 'eat' if k == 4 else 'feed'
                    if k == 4 and b not in what:
                        what[b] = 'stunned'
                    if k == 4 and colOf[a] != colOf[b]:
                        last_biter[b] = a
                        new_bites[a] = (sqOf[b], b)
                        if b in refills:
                            r = refills[b]
                            if a == r[0]:
                                r[3] += 1
                                if t == r[2] + 1:
                                    r[5] = 1           # bitten on its first live tick by the killer
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    for s, kil, kc, dc in pend_refill.get(t, []):
                        if s == y * W + x:
                            if c == dc:
                                refills[cid] = [kil, kc, t, 0, e, 0]
                                out[(kc, 'refill_seen')] += 1
                                out[(c, 'refilled')] += 1
                            elif c == kc:
                                out[(kc, 'took_own_kill')] += 1
                    for q in nbrs(y * W + x):
                        g = snap[q]
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
            for a, kind in cand.items():
                if isinstance(a, tuple):
                    continue
                act = what.get(a, 'none')
                if act == 'stunned':
                    continue
                out[(colOf[a], 'blind_' + kind + '_n')] += 1
                out[(colOf[a], 'blind_' + kind + '_' + act)] += 1
                if kind == 'empty':
                    why = cand[(a, 'why')]
                    out[(colOf[a], 'blind_empty_' + why + '_n')] += 1
                    out[(colOf[a], 'blind_empty_' + why + '_' + act)] += 1
            for a, (s, b) in new_bites.items():
                bit_sq[a] = (s, t)
                bit_tg[a] = b
            for b in dead:
                a = last_biter.get(b)
                if a is not None:
                    killer_of[b] = a
                if a is not None and b in sqOf:
                    pend_refill.setdefault(t + 1, []).append((sqOf[b], a, colOf[a], colOf[b]))
            pend_refill.pop(t, None)
            dead_all |= dead
            for cid in list(refills):
                kil, kc, tb, nb, e0, first = refills[cid]
                if cid in dead or t - tb >= 5:
                    out[(kc, 'refill_n')] += 1
                    out[(kc, 'refill_bit_first_tick')] += first
                    out[(kc, 'refill_killer_bites')] += nb
                    out[(kc, 'refill_child_energy')] += e0
                    out[(kc, 'refill_dead5')] += cid in dead
                    del refills[cid]
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
        for (c, k), n in out.items():
            name = nm[c] if c < len(nm) else 'colony %d' % c
            rows.append(dict(replay=rid, colony=c, name=name, measure=k, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'colony', 'name', 'measure', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
