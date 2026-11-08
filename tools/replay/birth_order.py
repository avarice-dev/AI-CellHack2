"""Birth order between colonies: for each birth of colony A in a tick where colony B also has births, is it before all
of B's births (pre), after all (post) or in between (mix)? Pooled per cell-name pair over the given replays, t >= tmin.
Events are in turn order, so this ranks each cell's split (refill) path cost against the others' (Sprint: 19 / 21 / 23).

Usage: python -I tools/replay/birth_order.py --pull <pull> <tmin> <replay id> [replay id ...]
  (data/<pull>/replays; colony names from data/<pull>/names.json or summaries/<id>.json)
"""
import gzip, struct, sys, json, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulls as P  # noqa: E402
ROOT = P.ROOT
PULL, ARGS = P.take_pull(sys.argv[1:], 'birth_order.py')
if len(ARGS) < 2:
    sys.exit('usage: python -I tools/replay/birth_order.py --pull <pull> <tmin> <replay id> [replay id ...]')
tmin = int(ARGS[0]); ids = [int(x) for x in ARGS[1:]]
NAMES = {}
for rid in ids:
    if not os.path.exists(P.pull_dir(PULL, 'replays', '%d.chr2.gz' % rid)):
        sys.exit('data/%s/replays/%d.chr2.gz not found: run a pull first (architecture/data-pulls.md)' % (PULL, rid))
    NAMES[rid] = P.load_names(PULL, rid)
    if NAMES[rid] is None:
        sys.exit('no colony names for %d in data/%s/names.json or summaries/: run tab.py first '
                 '(architecture/data-pulls.md)' % (rid, PULL))
agg = collections.defaultdict(lambda: [0, 0, 0])
for rid in ids:
    names = NAMES[rid]
    raw = gzip.decompress(open(P.pull_dir(PULL, 'replays', '%d.chr2.gz' % rid), 'rb').read())
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
