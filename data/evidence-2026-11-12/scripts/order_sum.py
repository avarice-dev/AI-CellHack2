"""Scratch: rival bite costs from order.csv.  Usage: python order_sum.py <out.txt> <order.csv>
Markers (our events of known instruction count) bracket each rival eat: lo <= cost <= hi (ties at both ends).
At a threshold X a rival eat is 'below' when a marker of cost X came after it (cost <= X) and 'above' when one came
before it (cost >= X).  F(X) = below / (below + above) ~ P(cost < X) + half of P(cost = X) (seeded coin on ties).
Per rival, era group (v2.0 games: markers 5, 11; v2.1/v2.2: 4, 16, 39; Conviction: 14), bite kind (first = the
eater did not eat this target on the previous tick, repeat = it did) and target (our cell, or anything else).
Our cell's first bite costs 16 in v2.1/v2.2 (5 in v2.0); the planned v2.3 first bite costs 11.
"""
import collections
import csv
import sys

rows = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
NORM = {'CogSpore - VarSi': 'VarSi', 'CogSpore-Siect-F': 'Siect-F', 'CogBloomXT v4': 'CogBloomXT'}
TH = (3, 4, 5, 11, 14, 16, 39)
C = collections.defaultdict(lambda: collections.Counter())
games = collections.defaultdict(set)
for r in rows:
    if r['rival'] == '_check':
        continue
    rv = NORM.get(r['rival'], r['rival'])
    eras = r['era'].split('+')
    eg = 'v2.0' if 'v2.0' in eras or 'v1' in eras else 'v2.2' if ('v2.2' in eras or 'v2.1' in eras) else 'conv'
    tg = 'ours' if r['target'] != 'other' else 'other'
    lo, hi, n = int(r['lo']), int(r['hi']), int(r['n'])
    for key in ((rv, eg, r['kind'], tg, r['window']), (rv, eg, r['kind'], tg, 'all'), (rv, 'ALL', r['kind'], tg, 'all')):
        c = C[key]
        c['n'] += n
        for x in TH:
            if hi <= x:
                c[('b', x)] += n
            elif lo >= x:
                c[('a', x)] += n
    games[(rv, eg)].add(r['replay'])
    games[(rv, 'ALL')].add(r['replay'])

out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P(__doc__)
rivals = sorted({k[0] for k in C}, key=lambda v: -sum(C[(v, 'ALL', k, t, 'all')]['n'] for k in ('first', 'repeat')
                                                     for t in ('ours',)))
P('%-16s %-4s %-6s %-5s %-3s %8s | %s' % ('rival', 'era', 'kind', 'tgt', 'w', 'eats', '  '.join(
    'F(%d) [inf]' % x for x in TH)))
for rv in rivals:
    for eg in ('v2.0', 'v2.2', 'conv', 'ALL'):
        if not games.get((rv, eg)):
            continue
        for kind in ('first', 'repeat'):
            for tg in ('ours', 'other'):
                for w in ('a', 'b', 'all'):
                    c = C.get((rv, eg, kind, tg, w))
                    if not c or c['n'] < 30:
                        continue
                    cells = []
                    for x in TH:
                        b, a = c[('b', x)], c[('a', x)]
                        cells.append('%5.1f [%3.0f%%]' % (100 * b / (a + b), 100 * (a + b) / c['n']) if a + b >= 20
                                     else '    -        ')
                    P('%-16s %-4s %-6s %-5s %-3s %8d | %s   (%d games)' % (rv, eg, kind, tg, w, c['n'], '  '.join(cells),
                                                                        len(games[(rv, eg)])))
    P('')
out.close()
