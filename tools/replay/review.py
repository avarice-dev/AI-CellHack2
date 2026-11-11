"""One row of measures for every colony of every replay of a pull (a whole-game review, all metrics at once).

For each colony: start square, distance to the nearest wall and to the nearest other start; cells at fixed ticks and
at the end; and, in each tick window, per cell-tick: splits (births), moves, feeds, eats; cells that could split and
did nothing (energy >= 5, an empty edge neighbour, no event: `hold`); cells at the cap with no event (`capidle`);
contact cell-ticks (an enemy on an edge neighbour at the start of the tick) and the share of them eaten before their
own action (`bitfirst`); deaths; enemy squares freed by a death beside the colony and the share it filled on the
next tick (`take`); own squares freed and the share it filled itself (`retake`).

Usage: python -I tools/replay/review.py --pull <pull> [replay id ...] [--csv=FILE]
Prints a table; --csv also writes every number.  Reads data/<pull>/replays and data/<pull>/names.json.
"""
import collections
import csv
import gzip
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulls as P  # noqa: E402

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))
POP_TICKS = (30, 60, 100, 200, 500)
WINDOWS = ((0, 30), (30, 60), (60, 100), (100, 200), (200, 3000))
CAP = 50


def review(path):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    start = {}
    pops = collections.defaultdict(dict)
    stat = collections.defaultdict(collections.Counter)      # (colony, window index) -> counters
    freed_prev = []                                           # (square, colony of the dead cell, colonies beside it)
    last_t = 0

    def win(t):
        for i, (a, b) in enumerate(WINDOWS):
            if a <= t < b:
                return i
        return len(WINDOWS) - 1

    def nbrs(s):
        x, y = s % W, s // W
        for dx, dy in DIRS:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                yield (y + dy) * W + x + dx

    while p < n_raw:
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8
            cells = []
            for _ in range(n):
                cells.append(BIRTH.unpack_from(raw, p)); p += 10
            if not loaded:
                for cid, c, x, y, e in cells:
                    ids.append(cid); colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                    start.setdefault(c, (x, y))
                loaded = True
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 4 + 8
            nev = U32.unpack_from(raw, p)[0]; p += 4
            w = win(t)
            last_t = t
            count = collections.Counter(colOf[c] for c in ids)
            if t in POP_TICKS:
                for c in range(ncol):
                    pops[c][t] = count.get(c, 0)
            snap = grid
            contact = set()
            for cid in ids:
                c = colOf[cid]
                stat[(c, w)]['cellticks'] += 1
                for s in nbrs(sqOf[cid]):
                    g = snap[s]
                    if g and colOf[g - 1] != c:
                        contact.add(cid)
                        break
            for cid in contact:
                stat[(colOf[cid], w)]['contact'] += 1
            # squares freed on the previous tick: who is on them now is decided by this tick's births
            freed_now = {s: (c, beside) for s, c, beside in freed_prev}
            grid = snap[:]
            acted, births, dead, bitten = set(), [], set(), set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    acted.add(a)
                    stat[(colOf[a], w)]['eat' if k == 4 else 'feed'] += 1
                    if k == 4 and b in contact and b not in acted and b not in bitten:
                        bitten.add(b)
                        stat[(colOf[b], w)]['bitfirst'] += 1
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                    births.append(cid)
                    stat[(c, w)]['birth'] += 1
                    fr = freed_now.pop(y * W + x, None)
                    if fr is not None:
                        owner, beside = fr
                        stat[(c, w)]['retook' if c == owner else 'took'] += 1
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0, s1 = sqOf[cid], y * W + x
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[s1] = cid + 1; sqOf[cid] = s1
                    acted.add(cid)
                    stat[(colOf[cid], w)]['move'] += 1
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                    stat[(colOf[cid], w)]['death'] += 1
                else:
                    raise ValueError(k)
            parents = set()
            for b in births:
                c = colOf[b]
                for s in nbrs(sqOf[b]):
                    g = snap[s]
                    if g and colOf[g - 1] == c and (g - 1) not in acted:
                        parents.add(g - 1)
            for cid in ids:
                if cid in acted or cid in parents or cid in dead or cid in bitten:
                    continue
                e = enOf.get(cid, 0)
                if e >= CAP:
                    stat[(colOf[cid], w)]['capidle'] += 1
                elif e >= 5 and any(snap[s] == 0 for s in nbrs(sqOf[cid])):
                    stat[(colOf[cid], w)]['hold'] += 1
            freed_prev = []
            for cid in dead:
                s = sqOf.pop(cid, None)
                if s is None:
                    continue
                if grid[s] == cid + 1:
                    grid[s] = 0
                owner = colOf[cid]
                beside = {colOf[grid[q] - 1] for q in nbrs(s) if grid[q]}
                freed_prev.append((s, owner, beside))
                for c in beside:
                    stat[(c, w)]['own_freed' if c == owner else 'enemy_freed'] += 1
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            ids = [i for i in ids if i not in dead] + [b for b in births if b not in dead]
            for cid, e in zip(ids, en):
                enOf[cid] = e
        elif rt == 3:
            p += 5 + 4 + 8
        else:
            raise ValueError((rt, p))
    final = collections.Counter(colOf[c] for c in ids)
    rows = []
    for c in range(ncol):
        x, y = start.get(c, (-1, -1))
        wall = min(x, y, W - 1 - x, H - 1 - y)
        other = min((abs(x - ox) + abs(y - oy) for oc, (ox, oy) in start.items() if oc != c), default=-1)
        row = {'colony': c, 'x': x, 'y': y, 'wall': wall, 'near': other, 'ticks': last_t + 1, 'final': final.get(c, 0)}
        for t in POP_TICKS:
            row['p%d' % t] = pops[c].get(t, 0)
        for i, (a, b) in enumerate(WINDOWS):
            s = stat[(c, i)]
            ct = max(s['cellticks'], 1)
            tag = 't%d' % a
            row[tag + '_split'] = round(100.0 * s['birth'] / ct, 1)
            row[tag + '_move'] = round(100.0 * s['move'] / ct, 1)
            row[tag + '_feed'] = round(100.0 * s['feed'] / ct, 1)
            row[tag + '_hold'] = round(100.0 * s['hold'] / ct, 1)
            row[tag + '_capidle'] = round(100.0 * s['capidle'] / ct, 1)
            row[tag + '_contact'] = round(100.0 * s['contact'] / ct, 1)
            row[tag + '_bitfirst'] = round(100.0 * s['bitfirst'] / max(s['contact'], 1), 1)
            row[tag + '_deaths'] = s['death']
            row[tag + '_take'] = round(100.0 * s['took'] / max(s['enemy_freed'], 1), 1)
            row[tag + '_enemyfreed'] = s['enemy_freed']
            row[tag + '_retake'] = round(100.0 * s['retook'] / max(s['own_freed'], 1), 1)
        rows.append(row)
    return rows


def main():
    pull, argv = P.take_pull(sys.argv[1:], 'review.py')
    opt = dict(a[2:].split('=', 1) if '=' in a else (a[2:], '1') for a in argv if a.startswith('--'))
    want = [a for a in argv if not a.startswith('--')]
    rdir = P.pull_dir(pull, 'replays')
    if not os.path.isdir(rdir) or not os.listdir(rdir):
        sys.exit('review.py: no replays in data/%s/replays: run a pull first' % pull)
    out = []
    for f in sorted(os.listdir(rdir)):
        rid = f.split('.')[0]
        if want and rid not in want:
            continue
        names = P.load_names(pull, rid)
        rows = review(os.path.join(rdir, f))
        order = sorted(rows, key=lambda r: -r['final'])
        for r in rows:
            r['replay'] = rid
            r['name'] = names[r['colony']] if names and r['colony'] < len(names) else 'colony %d' % r['colony']
            r['place'] = 1 + order.index(r)
        out += rows
    cols = ['replay', 'name', 'place', 'x', 'y', 'wall', 'near', 'p30', 'p60', 'p100', 'p200', 'final']
    print(' '.join('%-9s' % c if c in ('replay', 'name') else '%6s' % c for c in cols))
    for r in out:
        print(' '.join(('%-9s' % str(r[c])[:9]) if c in ('replay', 'name') else '%6s' % r[c] for c in cols))
    if 'csv' in opt:
        keys = ['replay', 'name', 'place'] + [k for k in out[0] if k not in ('replay', 'name', 'place')]
        with open(opt['csv'], 'w', newline='') as f:
            wr = csv.DictWriter(f, fieldnames=keys)
            wr.writeheader()
            wr.writerows(out)
        print('wrote %s (%d rows)' % (opt['csv'], len(out)))


if __name__ == '__main__':
    main()
