"""Freed squares per colony name, in a tick window: every cell death frees a square.  Who takes it within 5 ticks
(the dead cell's own colony, an enemy, or nobody), how many ticks later, and the newcomer's energy (a split child has
half its parent's).  Rows: the colony that took the square (claims), and the colony that lost it (losses).
Reads data/<pull>/replays and data/<pull>/names.json.

Usage: python -I tools/replay/freed_squares.py [--tmin=75] [--tmax=600] pull3 pull4 pull5
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
    pending = {}        # freed square -> (tick, colony that lost it)
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
            feeds, births, dead, acted, moved, enNew = [], [], set(), set(), [], {}
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if k == 5 and a not in acted and colOf.get(a) == colOf.get(b):
                        feeds.append((a, b))
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
                    acted.add(cid); moved.append(cid); enNew[cid] = enOf.get(cid, 0)
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            for cid in births + moved:
                s1 = sqOf.get(cid)
                f = pending.pop(s1, None)
                if f is not None:
                    t0, lost = f
                    e = enNew.get(cid, 0)
                    who = names[colOf[cid]]
                    out[who]['claims'] += 1; out[who]['claim_e'] += e; out[who]['claim_dt'] += t - t0
                    out[who]['claim_split' if cid in births else 'claim_move'] += 1
                    out[names[lost]]['lost_own' if colOf[cid] == lost else 'lost_enemy'] += 1
            for s1, (t0, lost) in list(pending.items()):
                if t - t0 > 5:
                    out[names[lost]]['lost_empty'] += 1
                    del pending[s1]
            if tmin <= t < tmax:
                for cid in dead:
                    if cid not in sqOf:
                        continue
                    s1, lost = sqOf[cid], colOf[cid]
                    g = grid[s1]
                    if g and g != cid + 1:          # taken in the same tick, after the death
                        n1 = g - 1
                        who = names[colOf[n1]]
                        out[who]['claims'] += 1; out[who]['claim_e'] += enNew.get(n1, enOf.get(n1, 0))
                        out[who]['claim_split' if n1 in births else 'claim_move'] += 1
                        out[names[lost]]['lost_own' if colOf[n1] == lost else 'lost_enemy'] += 1
                    else:
                        pending[s1] = (t, lost)
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
    tmin, tmax = int(opt.get('tmin', 75)), int(opt.get('tmax', 600))
    out = collections.defaultdict(collections.Counter)
    for pull in pulls:
        names = json.load(open(os.path.join(ROOT, 'data', pull, 'names.json'), encoding='utf-8'))
        rep = os.path.join(ROOT, 'data', pull, 'replays')
        for fn in sorted(os.listdir(rep)):
            rid = fn.split('.')[0]
            if fn.endswith('.chr2.gz') and rid in names:
                run(os.path.join(rep, fn), tmin, tmax, out, names[rid])
    print('t %d-%d, pulls %s' % (tmin, tmax, ' '.join(pulls)))
    print('%-12s %8s %8s %8s %8s %8s | %8s %8s %8s %8s' % ('cell', 'claims', 'split%', 'claim_e', 'ticks', 'move%',
                                                             'losses', 'own%', 'enemy%', 'empty%'))
    for nm, st in sorted(out.items(), key=lambda kv: -kv[1]['claims']):
        c = max(st['claims'], 1)
        l = st['lost_own'] + st['lost_enemy'] + st['lost_empty']
        if c < 500 and l < 500:
            continue
        L = max(l, 1)
        print('%-12s %8d %7.0f%% %8.1f %8.2f %7.0f%% | %8d %7.0f%% %7.0f%% %7.0f%%' % (
            nm, st['claims'], 100 * st['claim_split'] / c, st['claim_e'] / c, st['claim_dt'] / c,
            100 * st['claim_move'] / c, l, 100 * st['lost_own'] / L, 100 * st['lost_enemy'] / L,
            100 * st['lost_empty'] / L))


if __name__ == '__main__':
    main()
