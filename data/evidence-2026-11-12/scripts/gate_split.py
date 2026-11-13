"""Scratch (measure B1): contested empty squares, our best neighbour's raw state, episodes and fills (real replays).
A contested square = empty at tick start with cells of two or more colonies on its edges (squares freed by a death
the tick before excluded, as in lost_squares.py).  Views are the tick-start grid (sim/engine.py), so every flag below
is read from the tick-start snapshot.  Raw fields only; v2.2 rule labels are derived in gate_sum.py.

Rows (kind, key = '|'-joined fields, n = count):
  sq    per contested square-tick and colony: result (won/lost/open) | event of our best neighbour c (split > eat >
        move > feed > none > bitten, ties to higher energy) | c's energy 0..63 | direction of s from c (U/R/D/L) |
        enemy beside s on c's diagonal (0/1) | enemy straight beyond s (0/1) | c has any diagonal enemy (0/1) |
        c's refill pattern (any empty edge of c is a FREED_BY square: 0/1) | gate target of c is s (0/1) |
        c's empty edges (1-4) | rival (winner colony on lost squares, else the first enemy beside s)
  ep    per lost square episode (consecutive contested ticks of s for this colony, ending in a loss): ticks contested
        before the loss | ticks our best neighbour held (event none, e >= 5, a diagonal enemy, e below its gate
        threshold) | of those at e >= 8 | rival
  fill  per square this colony filled by a split: parent energy at tick start | parent's rule (gate: e >= threshold;
        rule4: below it) | direction | beside-diag | beyond | parent diagonal enemy | rival | child bitten on its
        first live tick (0/1) | child alive after 10 (0/1) | parent alive after 10 (0/1) | square held by this colony
        after 10 (0/1)
  hep   per episode (any outcome) in which our best neighbour held at least one tick: outcome (won / lost / left =
        no longer contested) | ticks contested | hold ticks | of those at e >= 8 | energy at the first hold tick
  hcx   near-hold cell-ticks as budget.py counts them, classed best / notbest / freed / uncontested
  hct   hold cell-ticks: distinct cells of this colony holding beside >= 1 contested square this tick | energy 0..63
  parent  split-parent attribution counts (match / ambiguous / nomatch / none); a child gets floor(parent e / 2)
Windows (budget.py's): a t < 30, b < 60, c < 100, d later.
Usage: python gate_split.py <replay dir> <names.json> <out.csv> [id ...]
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

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))          # UP RIGHT DOWN LEFT
DNAME = 'URDL'
PRIO = (2, 1, 0, 3)                                 # gate 1 split order DOWN, RIGHT, UP, LEFT
# FREED_BY (cells/gen_scourge.py) as (dx, dy) from the cell, per direction
FREED = {0: ((-1, -1), (1, -1)), 1: ((1, -1), (2, 0), (1, 1)), 2: ((-1, 1), (1, 1)), 3: ((-1, -1), (-2, 0), (-1, 1))}
ORDER = ('split', 'eat', 'move', 'feed', 'none', 'bitten', 'unknown')


def win(t):
    return 'a' if t < 30 else 'b' if t < 60 else 'c' if t < 100 else 'd'


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
    ep = {}                          # (square, colony) -> [ticks contested, hold5, hold8, energy at first hold]
    pend = []                        # fills waiting for their 1 / 10 tick checks
    dead_all = set()

    def nbrs(s):
        x, y = s % W, s // W
        for dx, dy in DIRS:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                yield (y + dy) * W + x + dx

    def look(snap, sc, s, ours):
        """Flags of our cell at sc for the square s beside it (tick-start snapshot)."""
        cx, cy = sc % W, sc // W

        def at(x, y):
            return snap[y * W + x] if 0 <= x < W and 0 <= y < H else -1

        def enemy(x, y):
            g = at(x, y)
            return g > 0 and colOf[g - 1] != ours
        d = DIRS.index((s % W - cx, s // W - cy))
        dx, dy = DIRS[d]
        side = enemy(cx + dx + dy, cy + dy + dx) or enemy(cx + dx - dy, cy + dy - dx)
        beyond = enemy(cx + 2 * dx, cy + 2 * dy)
        cdiag = any(enemy(cx + a, cy + b) for a in (-1, 1) for b in (-1, 1))
        empt = [k for k in PRIO if at(cx + DIRS[k][0], cy + DIRS[k][1]) == 0]
        fr = [k for k in empt if any(enemy(cx + a, cy + b) for a, b in FREED[k])]
        target = (fr or empt or [None])[0]
        return d, side, beyond, cdiag, bool(fr), target == d, len(empt)

    def rival_of(snap, s, ours):
        for q in nbrs(s):
            g = snap[q]
            if g and colOf[g - 1] != ours:
                return colOf[g - 1]
        return -1

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
            cand = collections.defaultdict(set)
            mine = collections.defaultdict(list)
            for cid in ids:
                for s in nbrs(sqOf[cid]):
                    if not snap[s]:
                        cand[s].add(colOf[cid])
                        mine[(s, colOf[cid])].append((cid, sqOf[cid]))
            contested = {s: cs for s, cs in cand.items() if len(cs) > 1 and s not in freed_prev}
            filled = {}
            grid = snap[:]
            what, dead, births = {}, set(), []
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
                    s = y * W + x
                    cnd = [g - 1 for g in (snap[q] for q in nbrs(s)) if g and colOf[g - 1] == c and (g - 1) not in what]
                    par, tag = RUN.parent(cnd, e)
                    if par is not None:
                        what[par] = 'split'
                    elif tag == 'unknown':
                        for g in cnd:
                            what[g] = 'unknown'
                    colOf[cid] = c; sqOf[cid] = s; grid[s] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    if s in contested and s not in filled:
                        filled[s] = (c, 'split')
                        if par is not None:
                            pe = enOf[par]
                            d, side, beyond, cdiag, fr, first, ne = look(snap, sqOf[par], s, c)
                            thr = 12 if fr else 16
                            pend.append([cid, par, t, c, w, s, '%s|%d|%s|%s|%d|%d|%d' % (
                                tag, pe, 'gate' if pe >= thr else 'rule4', DNAME[d], side, beyond, cdiag),
                                rival_of(snap, s, c), None])
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    what.setdefault(cid, 'move')
                    if y * W + x in contested and y * W + x not in filled:
                        filled[y * W + x] = (colOf[cid], 'move')
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            seen = set()
            holders = {}
            for s, cs in contested.items():
                f = filled.get(s)
                for ours in cs:
                    seen.add((s, ours))
                    res = 'open' if f is None else 'won' if f[0] == ours else 'lost'
                    best = None
                    for cid, sc in mine[(s, ours)]:
                        ev = what.get(cid, 'none')
                        e = enOf.get(cid, 0)
                        kk = (ORDER.index(ev), -e)
                        if best is None or kk < best[0]:
                            best = (kk, sc, ev, e)
                    _, sc, ev, e = best
                    d, side, beyond, cdiag, fr, first, ne = look(snap, sc, s, ours)
                    rv = f[0] if res == 'lost' else rival_of(snap, s, ours)
                    out[('sq', w, '%s|%s|%d|%s|%d|%d|%d|%d|%d|%d' % (res, ev, e, DNAME[d], side, beyond, cdiag, fr,
                                                                     first, ne), ours, rv)] += 1
                    e_ = ep.setdefault((s, ours), [0, 0, 0, -1])
                    held = ev == 'none' and e >= 5 and cdiag and e < (12 if fr else 16)
                    if held:
                        holders[(sc, ours)] = e
                    if res == 'lost':
                        out[('ep', w, '%d|%d|%d' % (e_[0], e_[1], e_[2]), ours, rv)] += 1
                    if res != 'open':
                        if e_[1]:
                            out[('hep', w, '%s|%d|%d|%d|%d' % (res, e_[0], e_[1], e_[2], e_[3]), ours, rv)] += 1
                        del ep[(s, ours)]
                    else:
                        e_[0] += 1
                        e_[1] += held
                        e_[2] += held and e >= 8
                        if held and e_[3] < 0:
                            e_[3] = e
            for (sc, ours), e in holders.items():
                out[('hct', w, '%d' % e, ours, -1)] += 1
            # hcx: every near-hold cell-tick as budget.py counts it (open, no enemy on an edge, an enemy on a diagonal,
            # 5-11 energy, no event), classed against this file's hct: best (= an hct holder), notbest (beside a
            # contested square, another own cell was its best neighbour), freed (its contested edge squares were all
            # freed by a death last tick: excluded here), uncontested (no empty edge square has an enemy beside it)
            for cid in ids:
                if what.get(cid, 'none') != 'none':
                    continue
                e = enOf.get(cid, 0)
                if not 5 <= e < 12:
                    continue
                c = colOf[cid]
                sc = sqOf[cid]
                cx, cy = sc % W, sc // W
                edge = list(nbrs(sc))
                if any(snap[q] and colOf[snap[q] - 1] != c for q in edge):
                    continue
                empt = [q for q in edge if not snap[q]]
                if not empt:
                    continue
                if not any(0 <= cx + a_ < W and 0 <= cy + b_ < H and snap[(cy + b_) * W + cx + a_]
                           and colOf[snap[(cy + b_) * W + cx + a_] - 1] != c for a_ in (-1, 1) for b_ in (-1, 1)):
                    continue
                if (sc, c) in holders:
                    cls = 'best'
                elif any(q in contested for q in empt):
                    cls = 'notbest'
                elif any(q in freed_prev and len(cand[q]) > 1 for q in empt):
                    cls = 'freed'
                else:
                    cls = 'uncontested'
                out[('hcx', w, cls, c, -1)] += 1
            for key in [k for k in ep if k not in seen]:
                e_ = ep.pop(key)                # no longer contested: the episode ended without a loss
                if e_[1]:
                    out[('hep', w, 'left|%d|%d|%d|%d' % (e_[0], e_[1], e_[2], e_[3]), key[1], -1)] += 1
            dead_all |= dead
            keep = []
            for it in pend:
                cid, par, tf, c, wf, sf, key, rv, b1 = it
                if t == tf + 1:
                    it[8] = int(what.get(cid) == 'bitten')
                if t >= tf + 10:
                    g = grid[sf]
                    out[('fill', wf, '%s|%s|%d|%d|%d' % (key, '%d' % (it[8] or 0), cid not in dead_all,
                                                         par not in dead_all, int(bool(g) and colOf[g - 1] == c and (g - 1) not in dead)),
                         c, rv)] += 1
                else:
                    keep.append(it)
            pend = keep
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
    for fn in sorted(os.listdir(rdir)):
        rid = fn.split('.')[0]
        if want and rid not in want:
            continue
        nm = names.get(rid, [])
        out = run(os.path.join(rdir, fn))
        for tag, n in RUN.count.items():
            out[('parent', '-', tag, -1, -1)] += n
        RUN.count.clear()
        for (kind, w, key, c, rv), n in out.items():
            name = nm[c] if 0 <= c < len(nm) else ''
            rname = nm[rv] if 0 <= rv < len(nm) else ''
            rows.append(dict(replay=rid, kind=kind, window=w, key=key, colony=c, name=name, rival=rname, n=n))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['replay', 'kind', 'window', 'key', 'colony', 'name', 'rival', 'n'])
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
