"""Scratch (design check a): is Siect-F's bite 3 instructions or 2?  Markers of exactly 3: our Conviction / Penalty
queue bites.  After a scan bite on target X at tick t0 (an eat on X with no eat on X by that cell on t0 - 1), the
queue plays k bites on X at t0 + 1 .. t0 + k, 3 instructions each (shr / or / jnz):
  Conviction: k = 0 if X's energy at t0 <= 2, else min(7, max(3, (e + 1) // 2 - 1))
  Penalty:    k = 0 if e <= 2; (e + 1) // 2 - 1 if e <= 8; else as Conviction
An eat on X by that cell at t0 + j, 1 <= j <= min(k, 3), is taken as a 3 marker (the queue cannot be empty then).
Also Bane v2.2 repeat bites (an eat on the target it ate on the previous tick) as 4 markers.
Turn order is by instruction count, ties by a seeded coin, so an eat of cost exactly 3 lands BETWEEN 3 markers
(lo = hi = 3) whenever a tick has several; a cost-2 eat never does (it comes before every 3).
For every Siect-F eat (on anyone): lo = largest marker cost before it in the tick's event order, hi = smallest after.
Classes: =3 (lo = hi = 3), <3 (hi = 3, lo < 3), 3-4 (lo = 3, hi = 4), =4, >4, other.
Usage: python order3.py <replay dir> <names.json> [id ...]
"""
import collections
import gzip
import json
import os
import struct
import sys


def run(path, names):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, enOf = {}, {}
    ids, loaded = [], False
    kind_of = {c: ('conv' if n == 'Conviction' else 'pen' if n == 'Penalty' else 'bane' if n == 'Bane v2.2' else
                   'siect' if 'Siect' in n else None) for c, n in enumerate(names)}
    prev = set()                 # (eater, target) eats on the previous tick
    scan = {}                    # our queue cell -> (target, tick of the scan bite, k)
    out = collections.Counter()
    while p < len(raw):
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8
            cells = [BIRTH.unpack_from(raw, p + 10 * i) for i in range(n)]; p += 10 * n
            if not loaded:
                for cid, c, x, y, e in cells:
                    ids.append(cid); colOf[cid] = c; enOf[cid] = e
                loaded = True
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 4 + 8
            nev = U32.unpack_from(raw, p)[0]; p += 4
            evs, births, dead = [], [], set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    evs.append((k, a, b))
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; enOf[cid] = e
                    births.append(cid)
                elif k == 2:
                    p += 9
                elif k == 3:
                    dead.add(U32.unpack_from(raw, p + 1)[0]); p += 5
                else:
                    raise ValueError(k)
            cost = [None] * len(evs)
            eats = set()
            for i, (k, a, b) in enumerate(evs):
                if k != 4 or colOf.get(a) == colOf.get(b):
                    continue
                ka = kind_of.get(colOf.get(a))
                if ka in ('conv', 'pen'):
                    sc = scan.get(a)
                    if sc and sc[0] == b and 1 <= t - sc[1] <= min(sc[2], 3):
                        cost[i] = 3
                    elif (a, b) not in prev:      # a scan bite: queue k bites on b
                        e = enOf.get(b, 0)
                        q = 0 if e <= 2 else min(7, max(3, (e + 1) // 2 - 1))
                        if ka == 'pen' and 2 < e <= 8:
                            q = (e + 1) // 2 - 1
                        scan[a] = (b, t, q)
                elif ka == 'bane' and (a, b) in prev:
                    cost[i] = 4
                eats.add((a, b))
            mk = [(i, c) for i, c in enumerate(cost) if c is not None]
            out['markers3'] += sum(1 for _, c in mk if c == 3)
            for i, (k, a, b) in enumerate(evs):
                if k != 4 or kind_of.get(colOf.get(a)) != 'siect' or colOf.get(a) == colOf.get(b):
                    continue
                lo = max([c for j, c in mk if j < i], default=0)
                hi = min([c for j, c in mk if j > i], default=999)
                cl = ('=3' if lo == hi == 3 else '<3' if hi == 3 and lo < 3 else '3-4' if lo == 3 and hi == 4 else
                      '=4' if lo == hi == 4 else '>4' if lo >= 4 and hi > 4 else 'other')
                out[cl] += 1
            prev = eats
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
    rdir, names_path = sys.argv[1:3]
    names = json.load(open(names_path, encoding='utf-8'))
    for rid in sys.argv[3:]:
        nm = [n.split(' ', 1)[-1] if not n[:1].isalnum() else n for n in names[rid]]
        nm = [n[:-2] if n.endswith((' W', ' L')) else n for n in nm]
        out = run(os.path.join(rdir, rid + '.chr2.gz'), nm)
        tot = sum(v for k, v in out.items() if k != 'markers3')
        print(rid, nm, '| our 3-markers %d | Siect-F eats %d:' % (out['markers3'], tot),
              ' '.join('%s %.1f%%' % (k, 100.0 * out[k] / max(tot, 1)) for k in ('<3', '=3', '3-4', '=4', '>4', 'other')))
