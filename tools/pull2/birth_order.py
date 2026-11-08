"""Birth order between colonies: for each birth of colony A in a tick where colony B also has births, is it before all
of B's births (pre), after all (post) or in between (mix)? Pooled per cell-name pair over the given replays, t >= tmin.
Events are in turn order, so this ranks each cell's split (refill) path cost against the others' (Sprint: 19 / 21 / 23).

Usage: python -I tools/pull2/birth_order.py <tmin> <replay id> [replay id ...]   (data/pull2 replays and summaries)
"""
import gzip, struct, sys, json, collections, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if len(sys.argv) < 3:
    sys.exit('usage: python -I tools/pull2/birth_order.py <tmin> <replay id> [replay id ...]')
tmin = int(sys.argv[1]); ids = [int(x) for x in sys.argv[2:]]
for rid in ids:
    for sub, ext in (('summaries', 'json'), ('replays', 'chr2.gz')):
        if not os.path.exists(os.path.join(ROOT, 'data', 'pull2', sub, '%d.%s' % (rid, ext))):
            sys.exit('data/pull2/%s/%d.%s not found: run a pull first (architecture/data-pulls.md)' % (sub, rid, ext))
agg = collections.defaultdict(lambda: [0, 0, 0])
for rid in ids:
    s = json.load(open(os.path.join(ROOT, 'data', 'pull2', 'summaries', '%d.json' % rid), encoding='utf-8'))
    names = [n.split(' ', 1)[-1] for n in s['names']]
    raw = gzip.decompress(open(os.path.join(ROOT, 'data', 'pull2', 'replays', '%d.chr2.gz' % rid), 'rb').read())
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    while p < len(raw):
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8 + 10 * n
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 12
            nev = U32.unpack_from(raw, p)[0]; p += 4
            seq = []
            for j in range(nev):
                k = raw[p]
                if k in (4, 5): p += 10
                elif k == 1:
                    c = raw[p + 5]; p += 11
                    if t >= tmin: seq.append(c)
                elif k == 2: p += 9
                elif k == 3: p += 5
            n = U32.unpack_from(raw, p)[0]; p += 4 + n
            if seq:
                cols = set(seq)
                for a in cols:
                    for b in cols:
                        if a == b: continue
                        first_b = seq.index(b); last_b = len(seq) - 1 - seq[::-1].index(b)
                        for j, c in enumerate(seq):
                            if c != a: continue
                            g = agg[(names[a], names[b])]
                            if j < first_b: g[0] += 1
                            elif j > last_b: g[2] += 1
                            else: g[1] += 1
        elif rt == 3:
            p += 17
for (a, b), (pre, mix, post) in sorted(agg.items()):
    n = pre + mix + post
    if n >= 300:
        print('%-12s before %-12s pre %3.0f%% mix %3.0f%% post %3.0f%%  n %d' % (a, b, 100*pre/n, 100*mix/n, 100*post/n, n))
