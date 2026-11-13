"""Scratch: why our colony loses contested empty squares (an empty square with cells of two or more colonies on
its edges at the start of the tick; squares freed by a death the tick before are excluded, they are 'take').
For every contested square-tick where our colony has a neighbour, the outcome (won / lost / open) and the state of
our best-placed neighbour, classified in this order:
  split  - a neighbour of ours split this tick (we cannot see the target square in the replay; 'split' on a lost
           square means a split elsewhere or into it too late, it fails silently only when the square is taken
           first, so 'none e>=12' below is the usual lost-race signature)
  eat    - a neighbour bit an enemy (the bite came first in its program)
  bitten - every neighbour was bitten before its turn (stunned)
  feed / move
  none e>=12, none 5-11, none <5  - no event (rest, hold, or a split that lost the race / hit an occupied square)
Also the winner's way in (split or move) on lost squares, and every fill of a contested square: filler energy
(child energy for a split, mover energy for a move), alive after 5 / 10 ticks, square held by the same colony after 10
(rows result = fill-split:n / :alive5 / :alive10 / :held10, state = energy bucket).
Usage: python lost_squares.py <replay dir> <names.json> <out.csv> [id ...]   (every colony of every game)
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

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))




RUN = parents.Running()


def run(path):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    freed_prev = {}
    out = collections.Counter()
    pending = {}                     # filler cell id -> [colony, tick, energy bucket, square, kind, window]
    dead_all = set()

    def eb(e):
        return '1-2' if e <= 2 else '3-4' if e <= 4 else '5-6' if e <= 6 else '7-9' if e <= 9 else '10+'

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
            cand = collections.defaultdict(set)
            mine = collections.defaultdict(list)            # (contested square, colony) -> its neighbour cell ids
            for cid in ids:
                for s in nbrs(sqOf[cid]):
                    if not snap[s]:
                        cand[s].add(colOf[cid])
                        mine[(s, colOf[cid])].append(cid)
            contested = {s: cs for s, cs in cand.items() if len(cs) > 1 and s not in freed_prev}
            filled = {}
            grid = snap[:]
            what, births, dead = {}, [], set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    RUN.event(k, a, b)
                    if a not in what:
                        what[a] = 'eat' if k == 4 else 'feed'
                    if k == 4 and b not in what:
                        what[b] = 'bitten'
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    if y * W + x in contested and y * W + x not in filled:
                        filled[y * W + x] = (c, 'split')
                        pending[cid] = [c, t, eb(e), y * W + x, 'split', 'a' if t < 60 else 'b' if t < 100 else 'c']
                    cand = [g - 1 for g in (snap[q] for q in nbrs(y * W + x)) if g and colOf[g - 1] == c and (g - 1) not in what]
                    par, tag = RUN.parent(cand, e)
                    if par is not None:
                        what[par] = 'split'
                    elif tag == 'unknown':
                        for g in cand:
                            what[g] = 'unknown'
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    what.setdefault(cid, 'move')
                    if y * W + x in contested and y * W + x not in filled:
                        filled[y * W + x] = (colOf[cid], 'move')
                        pending[cid] = [colOf[cid], t, eb(enOf.get(cid, 0)), y * W + x, 'move',
                                        'a' if t < 60 else 'b' if t < 100 else 'c']
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            w = 'a' if t < 60 else 'b' if t < 100 else 'c'
            for s, cs in contested.items():
              f = filled.get(s)
              for ours in cs:
                res = 'open' if f is None else 'won' if f[0] == ours else 'lost'
                states = []
                for cid in mine[(s, ours)]:
                    ev = what.get(cid, 'none')
                    e = enOf.get(cid, 0)
                    if ev == 'none':
                        ev = 'none e>=12' if e >= 12 else 'none 5-11' if e >= 5 else 'none <5'
                    states.append(ev)
                order = ('split', 'eat', 'none e>=12', 'move', 'feed', 'none 5-11', 'none <5', 'bitten', 'unknown')
                best = min(states, key=order.index)
                out[(ours, w, res, best)] += 1
                if res == 'lost':
                    out[(ours, w, 'lost-by', f[1])] += 1
                elif res == 'won':
                    out[(ours, w, 'won-by', f[1])] += 1
            dead_all |= dead
            for cid in list(pending):
                c, tf, b, sq, kind, win = pending[cid]
                key = (c, win, 'fill-' + kind, b)
                if t - tf == 5:
                    out[key + ('n',)] += 1
                    out[key + ('alive5',)] += cid not in dead_all
                if t - tf == 10:
                    out[key + ('alive10',)] += cid not in dead_all
                    g = grid[sq]
                    out[key + ('held10',)] += bool(g) and colOf[g - 1] == c
                    del pending[cid]
            freed_prev = {}
            for cid in dead:
                s = sqOf.pop(cid, None)
                if s is None:
                    continue
                if grid[s] == cid + 1:
                    grid[s] = 0
                freed_prev[s] = colOf[cid]
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
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
        for key, n in out.items():
            c, w, res, best = key[:4]
            if len(key) == 5:                      # fills: result = fill-split / fill-move, state = energy bucket
                res, best = res + ':' + key[4], best
            name = nm[c] if c < len(nm) else 'colony %d' % c
            rows.append(dict(replay=rid, colony=c, name=name, window=w, result=res, state=best, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'colony', 'name', 'window', 'result', 'state', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
    print('parent attribution', dict(RUN.count))
