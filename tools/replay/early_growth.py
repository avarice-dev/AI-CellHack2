"""Early growth per colony name, in a tick window (default t0-75): per cell-tick the share that split (births / cells),
fed, moved, ate or had no event (rest, stun, blocked); the mean child energy at birth (a child has half its parent's,
rounded down); the share of feeds into a friend with an empty neighbour; population at the window end.
Reads data/<pull>/replays and data/<pull>/names.json.

Usage: python -I tools/replay/early_growth.py [--tmin=0] [--tmax=75] pull3 pull4 pull5
"""
import collections
import gzip
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def run(path, tmin, tmax, out, names):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
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
                loaded = True
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 4 + 8
            nev = U32.unpack_from(raw, p)[0]; p += 4
            snap, sq0, en0 = grid[:], dict(sqOf), dict(enOf)
            feeds, births, dead, acted, moved, enNew, eats = [], [], set(), set(), [], {}, []
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if a not in acted:
                        if k == 5:
                            feeds.append((a, b))
                        else:
                            eats.append(a)
                    acted.add(a)
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                    births.append(cid); enNew[cid] = e
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    acted.add(cid); moved.append(cid)
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            if tmin <= t < tmax:
                seen = collections.Counter(colOf[c] for c in sq0)
                for c, k in seen.items():
                    st = out[names[c]]
                    st['cellticks'] += k; st['ticks'] += 1
                for cid in births:
                    st = out[names[colOf[cid]]]
                    st['births'] += 1; st['child_e'] += enNew[cid]
                for a, b in feeds:
                    st = out[names[colOf[a]]]
                    st['feeds'] += 1
                    s1 = sq0.get(b)
                    if s1 is not None:
                        x, y = s1 % W, s1 // W
                        if any(0 <= x + dx < W and 0 <= y + dy < H and not snap[(y + dy) * W + x + dx] for dx, dy in DIRS):
                            st['feed_grow'] += 1
                for cid in eats:
                    out[names[colOf[cid]]]['eats'] += 1
                for cid in moved:
                    out[names[colOf[cid]]]['moves'] += 1
            if t % 5 == 4 and t < tmax:
                for c, k in collections.Counter(colOf[c] for c in sqOf if c not in dead).items():
                    out[names[c]]['curve%d' % (t + 1)] += k
            if t == tmax - 1:
                for c, k in collections.Counter(colOf[c] for c in sqOf if c not in dead).items():
                    out[names[c]]['pop_end'] += k; out[names[c]]['games'] += 1
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
            raise ValueError((rt, p, n_raw))


def main():
    opt = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--'))
    pulls = [a for a in sys.argv[1:] if not a.startswith('--')]
    tmin, tmax = int(opt.get('tmin', 0)), int(opt.get('tmax', 75))
    out = collections.defaultdict(collections.Counter)
    for pull in pulls:
        names = json.load(open(os.path.join(ROOT, 'data', pull, 'names.json'), encoding='utf-8'))
        rep = os.path.join(ROOT, 'data', pull, 'replays')
        for fn in sorted(os.listdir(rep)):
            rid = fn.split('.')[0]
            if fn.endswith('.chr2.gz') and rid in names:
                run(os.path.join(rep, fn), tmin, tmax, out, names[rid])
    print('t %d-%d, pulls %s' % (tmin, tmax, ' '.join(pulls)))
    print('%-12s %6s %8s %7s %7s %7s %7s %7s %8s %9s' % ('cell', 'games', 'pop_end', 'split%', 'feed%', 'eat%',
                                                          'move%', 'idle%', 'child_e', 'feed_grow'))
    for nm, st in sorted(out.items(), key=lambda kv: -kv[1]['pop_end'] / max(kv[1]['games'], 1)):
        if st['games'] < 10:
            continue
        ct = max(st['cellticks'], 1)
        busy = st['births'] + st['feeds'] + st['eats'] + st['moves']
        print('%-12s %6d %8.0f %6.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%% %8.1f %8.0f%%' % (
            nm, st['games'], st['pop_end'] / st['games'], 100 * st['births'] / ct, 100 * st['feeds'] / ct,
            100 * st['eats'] / ct, 100 * st['moves'] / ct, 100 * (ct - busy) / ct,
            st['child_e'] / max(st['births'], 1), 100 * st['feed_grow'] / max(st['feeds'], 1)))
    curve(out, tmax)


def curve(out, tmax):
    pts = list(range(5, tmax + 1, 5))
    print('population after tick (mean over games):')
    print('%-12s ' % 'cell' + ' '.join('%5d' % t for t in pts))
    for nm, st in sorted(out.items(), key=lambda kv: -kv[1]['pop_end'] / max(kv[1]['games'], 1)):
        if st['games'] >= 10:
            print('%-12s ' % nm + ' '.join('%5.0f' % (st['curve%d' % t] / st['games']) for t in pts))


if __name__ == '__main__':
    main()
