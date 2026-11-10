"""Bite targeting per colony name: for every bite (eat of an adjacent enemy) in a tick window, the victim's energy at
the start of the tick, whether the victim died that tick, and, when the eater had 2 or more enemy neighbours with
different energies, whether it chose the poorest or the richest of them.  Reads data/<pull>/replays and
data/<pull>/names.json.

Usage: python -I tools/replay/bite_targets.py [--tmin=75] [--tmax=200] pull3 pull4 pull5
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
            bites, births, dead, acted = [], [], set(), set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if k == 4 and a not in acted and colOf.get(a) != colOf.get(b):
                        bites.append((a, b))
                    acted.add(a)
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
                    acted.add(cid)
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            if tmin <= t < tmax:
                for a, b in bites:
                    if a not in sq0 or b not in en0:
                        continue
                    st = out[names[colOf[a]]]
                    st['bites'] += 1
                    st['victim_e'] += en0[b]
                    st['kills'] += b in dead
                    st['victim_lt5'] += en0[b] < 5
                    s = sq0[a]; x, y = s % W, s // W
                    es = []
                    for dx, dy in DIRS:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H:
                            g = snap[ny * W + nx]
                            if g and colOf[g - 1] != colOf[a] and (g - 1) in en0:
                                es.append(en0[g - 1])
                    if len(es) >= 2 and min(es) != max(es):
                        st['choice'] += 1
                        st['poorest'] += en0[b] == min(es)
                        st['richest'] += en0[b] == max(es)
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
    tmin, tmax = int(opt.get('tmin', 75)), int(opt.get('tmax', 200))
    out = collections.defaultdict(collections.Counter)
    for pull in pulls:
        names = json.load(open(os.path.join(ROOT, 'data', pull, 'names.json'), encoding='utf-8'))
        rep = os.path.join(ROOT, 'data', pull, 'replays')
        for fn in sorted(os.listdir(rep)):
            rid = fn.split('.')[0]
            if fn.endswith('.chr2.gz') and rid in names:
                run(os.path.join(rep, fn), tmin, tmax, out, names[rid])
    print('t %d-%d, pulls %s' % (tmin, tmax, ' '.join(pulls)))
    print('%-12s %8s %8s %8s %8s %8s %8s %8s' % ('cell', 'bites', 'kill%', 'vic_e', 'vic<5%', 'choices', 'poorest', 'richest'))
    for nm, st in sorted(out.items(), key=lambda kv: -kv[1]['bites']):
        if st['bites'] < 2000:
            continue
        b, c = st['bites'], max(st['choice'], 1)
        print('%-12s %8d %7.1f%% %8.1f %7.1f%% %8d %7.0f%% %7.0f%%' % (
            nm, b, 100 * st['kills'] / b, st['victim_e'] / b, 100 * st['victim_lt5'] / b, st['choice'],
            100 * st['poorest'] / c, 100 * st['richest'] / c))


if __name__ == '__main__':
    main()
