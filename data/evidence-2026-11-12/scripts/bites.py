"""Scratch: the bite side of the front, per colony, from real replays (no cell code, no models).
Per colony and window (a t<60, b 60-100, c 100-300, d 300+):
  eats_enemy, eats_friend (bites on own cells), kills (bites that left the target at 0)
  chain: bites by one cell on the same target on consecutive ticks (mean chain length, chains)
  after_kill: what the killer did on the next tick: take (split into the freed square), split (elsewhere), eat
             (another bite), move, feed, bitten (stunned), none (no event: rest, hold, or a bite/split that missed)
  freed_by_kill taken next tick by: killer's colony / other colony / nobody
  stunned: our cells bitten before their turn per tick of contact (an enemy on an edge at tick start)
  bitten_low: cells bitten while at energy <= 2 (die to one bite) / <= 4
Usage: python bites.py <replay dir> <names.json> <out.csv> [id ...]
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


def win(t):
    return 'a' if t < 60 else 'b' if t < 100 else 'c' if t < 300 else 'd'


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
    out = collections.Counter()
    last_bite = {}                   # eater -> (target, tick)
    chain = {}                       # eater -> current chain length
    killers = {}                     # tick+1 -> list of (killer, freed square, killer colony)
    freed_watch = {}                 # square freed by a kill at t -> (killer colony, t)

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
            w = win(t)
            snap = grid
            contact = set()
            for cid in ids:
                c = colOf[cid]
                if any(snap[s] and colOf[snap[s] - 1] != c for s in nbrs(sqOf[cid])):
                    contact.add(cid)
            for cid in contact:
                out[(colOf[cid], w, 'contact')] += 1
            grid = snap[:]
            what, births, dead = {}, [], set()
            en_now = dict(enOf)
            bit_this = {}
            last_biter = {}
            born_at = {}
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    RUN.event(k, a, b)
                    if a not in what:
                        what[a] = 'eat' if k == 4 else 'feed'
                    if k == 4:
                        ca, cb = colOf[a], colOf[b]
                        eb = en_now.get(b, 0)
                        if b not in what:
                            what[b] = 'bitten'
                            if cb != ca:
                                out[(cb, w, 'stunned')] += 1
                        if ca == cb:
                            out[(ca, w, 'eats_friend')] += 1
                        else:
                            out[(ca, w, 'eats_enemy')] += 1
                            out[(cb, w, 'bitten_total')] += 1
                            out[(cb, w, 'bitten_le2')] += eb <= 2
                            out[(cb, w, 'bitten_le4')] += eb <= 4
                        take = 2 if eb > 2 else eb
                        en_now[b] = eb - take
                        en_now[a] = min(50, en_now.get(a, 0) + take)
                        if ca != cb:
                            bit_this[a] = b
                            last_biter[b] = a
                    else:
                        eg = en_now.get(a, 0)
                        give = 2 if eg > 2 else eg
                        en_now[a] = eg - give
                        en_now[b] = min(50, en_now.get(b, 0) + give)
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    born_at[y * W + x] = c
                    cand = [g - 1 for g in (snap[q] for q in nbrs(y * W + x)) if g and colOf[g - 1] == c and (g - 1) not in what]
                    parent, tag = RUN.parent(cand, e)          # shared matcher (parents.py)
                    if parent is not None:
                        what[parent] = 'split'
                    elif tag == 'unknown':
                        for g in cand:
                            what[g] = 'unknown'
                    if parent is not None:
                        what[('sq', parent)] = y * W + x
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    what.setdefault(cid, 'move')
                    born_at.setdefault(y * W + x, colOf[cid])
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            for b in dead:                                 # kills: died this tick after an enemy bite
                a = last_biter.get(b)
                if a is not None:
                    out[(colOf[a], w, 'kills')] += 1
                    killers.setdefault(t + 1, []).append((a, sqOf[b], colOf[a]))
            # chains
            for a, b in bit_this.items():
                lb = last_bite.get(a)
                if lb and lb[0] == b and lb[1] == t - 1:
                    chain[a] += 1
                else:
                    if a in chain:
                        out[(colOf[a], w, 'chains')] += 1
                        out[(colOf[a], w, 'chain_len')] += chain[a]
                    chain[a] = 1
                last_bite[a] = (b, t)
            # after a kill last tick: the killer's action now
            for a, sq, ca in killers.pop(t, []):
                if a in dead or a not in colOf:
                    continue
                act = what.get(a, 'none')
                if act == 'split' and what.get(('sq', a)) == sq:
                    act = 'take'
                out[(ca, w, 'after_kill_' + act)] += 1
                out[(ca, w, 'after_kill_n')] += 1
                owner = born_at.get(sq)
                out[(ca, w, 'freed_next_' + ('own' if owner == ca else 'nobody' if owner is None else 'other'))] += 1
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
    for a, L in chain.items():
        if a in colOf:
            out[(colOf[a], 'all', 'chains')] += 1
            out[(colOf[a], 'all', 'chain_len')] += L
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
        for (c, w, k), n in out.items():
            name = nm[c] if c < len(nm) else 'colony %d' % c
            rows.append(dict(replay=rid, colony=c, name=name, window=w, measure=k, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'colony', 'name', 'window', 'measure', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
