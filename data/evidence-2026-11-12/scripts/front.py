"""Scratch: the front, per colony.  (1) Children born on a square freed the tick before by an ENEMY death
('took'): count, child energy (mean, share <= 2 = dies to one bite, <= 4), share dead within 5 ticks.
(2) Contact cell-ticks (an enemy on an edge neighbour at the start of the tick): share that ate, fed, split,
moved, were bitten before acting, or had no event ('none'), and 'none' split by own energy < 5 / >= 5.
Same replay reading as tools/replay/review.py.
Usage: python front.py <replay dir> <names.json> <out.csv> [tmin] [id ...]
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


def front(path, tmin):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    st = collections.defaultdict(collections.Counter)
    freed_prev = {}
    watch = {}                       # child id -> (colony, tick born) for the 5-tick survival check
    adj_prev = {}                    # cell id -> enemy ids beside it at the start of the previous tick
    first = {}                       # (colony a, colony b), a < b -> (tick of first edge contact, closer list)
    moved_at = {}                    # cell id -> last tick it was born or moved
    bites = collections.Counter()    # (eater colony, eaten colony) -> eats
    took_from = collections.Counter()  # (taker colony, colony of the dead cell) -> births on its freed square

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
            on = t >= tmin
            snap = grid
            contact = set()
            fresh = set()
            adj_now = {}
            if on:
                for cid in ids:
                    c = colOf[cid]
                    en_ids = frozenset(snap[s] - 1 for s in nbrs(sqOf[cid]) if snap[s] and colOf[snap[s] - 1] != c)
                    if en_ids:
                        contact.add(cid)
                        adj_now[cid] = en_ids
                        for e in en_ids:
                            oc = colOf[e]
                            key = (min(c, oc), max(c, oc))
                            if key not in first:
                                closers = set()
                                if moved_at.get(cid) == t - 1:
                                    closers.add(c)
                                if moved_at.get(e) == t - 1:
                                    closers.add(oc)
                                first[key] = (t, sorted(closers))
                        if not en_ids <= adj_prev.get(cid, frozenset()):
                            fresh.add(cid)              # an enemy beside me that was not beside me last tick
            adj_prev = adj_now
            contested = {}                                  # empty square -> colonies with a cell beside it
            if on:
                cand = collections.defaultdict(set)
                for cid in ids:
                    for s in nbrs(sqOf[cid]):
                        if not snap[s]:
                            cand[s].add(colOf[cid])
                contested = {s: cs for s, cs in cand.items() if len(cs) > 1}
            filled = {}                                     # contested square -> colony that entered it first
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
                    if k == 4 and on and colOf[a] != colOf[b]:
                        bites[(colOf[a], colOf[b])] += 1
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    moved_at[cid] = t
                    if y * W + x in contested:
                        filled.setdefault(y * W + x, c)
                    owner = freed_prev.get(y * W + x)
                    if on and owner is not None and owner != c:
                        took_from[(c, owner)] += 1
                    if on and owner is not None and owner != c:
                        s = st[c]
                        s['took'] += 1; s['took_e'] += e
                        s['took_e2'] += e <= 2; s['took_e4'] += e <= 4
                        watch[cid] = (c, t)
                    cand = [g - 1 for g in (snap[q] for q in nbrs(y * W + x)) if g and colOf[g - 1] == c and (g - 1) not in what]
                    parent, tag = RUN.parent(cand, e)          # shared matcher (parents.py)
                    if parent is not None:
                        what[parent] = 'split'
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
                    moved_at[cid] = t
                    if y * W + x in contested:
                        filled.setdefault(y * W + x, colOf[cid])
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            for cid in contact:
                s = st[colOf[cid]]
                w = what.get(cid, 'none')
                s['contact'] += 1
                s['c_' + w] += 1
                kind = 'fr' if cid in fresh else 'on'
                s[kind] += 1
                s[kind + '_' + w] += 1
                if w == 'none':
                    s['none_lo' if enOf.get(cid, 0) < 5 else 'none_hi'] += 1
            for sq, cs in contested.items():
                if sq in freed_prev:                           # freed by a death last tick: counted as take
                    continue
                f = filled.get(sq)
                w = 'a' if t < 60 else 'b' if t < 100 else 'c'   # contested squares in t0-60 / t60-100 / t100+
                for c in cs:
                    s = st[c]
                    s['ct_' + w] += 1
                    if f == c:
                        s['ctw_' + w] += 1
                    elif f is not None:
                        s['ctl_' + w] += 1
            freed_prev = {}
            for cid in dead:
                s = sqOf.pop(cid, None)
                if s is None:
                    continue
                if grid[s] == cid + 1:
                    grid[s] = 0
                freed_prev[s] = colOf[cid]
                if cid in watch:
                    c, tb = watch.pop(cid)
                    if t - tb <= 5:
                        st[c]['took_dead5'] += 1
            for cid in [c for c, (col, tb) in watch.items() if t - tb > 5]:
                del watch[cid]
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            ids = [i for i in ids if i not in dead] + [b for b in births if b not in dead]
            for cid, e in zip(ids, en):
                enOf[cid] = e
        elif rt == 3:
            p += 5 + 4 + 8
        else:
            raise ValueError((rt, p))
    return st, ncol, first, bites, took_from


if __name__ == '__main__':
    rdir, names_path, out = sys.argv[1:4]
    tmin = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    want = set(sys.argv[5:])
    names = json.load(open(names_path, encoding='utf-8'))
    rows = []
    for f in sorted(os.listdir(rdir)):
        rid = f.split('.')[0]
        if want and rid not in want:
            continue
        st, ncol, first, bites, took_from = front(os.path.join(rdir, f), tmin)
        nm = names.get(rid, [])
        for c in range(ncol):
            s = st[c]
            others = [o for o in range(ncol) if o != c]
            extra = dict(
                first=json.dumps({o: first.get((min(c, o), max(c, o)), (-1, []))[0] for o in others}),
                closed=json.dumps({o: c in first.get((min(c, o), max(c, o)), (-1, []))[1] for o in others}),
                bites_on=json.dumps({o: bites[(c, o)] for o in others}),
                bitten_by=json.dumps({o: bites[(o, c)] for o in others}),
                took_from=json.dumps({o: took_from[(c, o)] for o in others}))
            ct, tk = max(s['contact'], 1), max(s['took'], 1)
            name = nm[c] if c < len(nm) else 'colony %d' % c
            name = name.split(' ', 1)[-1] if not name[:1].isalnum() else name
            row = dict(replay=rid, name=name, contact=s['contact'], took=s['took'],
                       took_e=round(s['took_e'] / tk, 2), took_e2=round(100 * s['took_e2'] / tk, 1),
                       took_e4=round(100 * s['took_e4'] / tk, 1), took_dead5=round(100 * s['took_dead5'] / tk, 1))
            for w in ('eat', 'feed', 'split', 'move', 'bitten', 'none'):
                row['c_' + w] = round(100 * s['c_' + w] / ct, 1)
            row['none_lo'] = round(100 * s['none_lo'] / ct, 1)
            row['none_hi'] = round(100 * s['none_hi'] / ct, 1)
            for kind in ('fr', 'on'):                     # fresh / ongoing contact
                n = max(s[kind], 1)
                row[kind] = s[kind]
                for w in ('eat', 'bitten', 'none'):
                    row[kind + '_' + w] = round(100 * s[kind + '_' + w] / n, 1)
            for w in ('a', 'b', 'c'):                     # contested empty squares: count, won %, lost %
                n = max(s['ct_' + w], 1)
                row['ct_' + w] = s['ct_' + w]
                row['ctw_' + w] = round(100 * s['ctw_' + w] / n, 1)
                row['ctl_' + w] = round(100 * s['ctl_' + w] / n, 1)
            row['colony'] = c
            row.update(extra)
            rows.append(row)
        print(rid, 'done', flush=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print('wrote', out, len(rows))
