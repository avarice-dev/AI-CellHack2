"""Scratch: pool duel.csv per (cell A, cell B) from A's side.  Usage: python duel_sum.py <out.txt> <duel.csv>
A pair-tick = two enemy cells that are edge neighbours at tick start, both alive.  'armed' = bit this opponent on the
previous tick.  States: fresh (neither armed), A armed only, B armed only, both armed.  Per state: pair-ticks, A bit
first %, B bit first %, neither %.  Windows: a = t < 100, b = t >= 100, all = both.
Read: in 'fresh' the faster first bite wins; in 'B armed' A only escapes if A's first bite beats B's repeat bite.
"""
import collections
import csv
import sys


def label(n, rid):
    if n != 'Bane':
        return n
    rid = int(rid)
    return 'Bane v1' if rid < 124690 else 'Bane v2.0' if rid < 126000 else 'Bane v2.1' if rid < 127810 else 'Bane v2.2'


rows = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
C = collections.defaultdict(collections.Counter)      # (A, B, window, state) -> {A, B, n}
games = collections.defaultdict(set)
for r in rows:
    x, y = (lambda n: {'Bane v2': 'Bane v2.0'}.get(n, n))(label(r['x'], r['replay'])), (lambda n: {'Bane v2': 'Bane v2.0'}.get(n, n))(label(r['y'], r['replay']))
    if x == y:
        continue
    xa, ya, res, n = int(r['x_armed']), int(r['y_armed']), r['result'], int(r['n'])
    for A, B, aa, ba, ra in ((x, y, xa, ya, {'x': 'A', 'y': 'B', 'n': 'n'}[res]),
                             (y, x, ya, xa, {'x': 'B', 'y': 'A', 'n': 'n'}[res])):
        st = 'fresh' if not aa and not ba else 'A armed' if aa and not ba else 'B armed' if ba and not aa else 'both'
        for w in (r['window'], 'all'):
            C[(A, B, w, st)][ra] += n
        games[(A, B)].add(r['replay'])
FOCUS = ('Bane v2.2', 'Bane v2.1', 'Bane v2.0', 'Conviction', 'Penalty', 'VarSi', 'Siect-F', 'Colossus', 'CogSpore',
         'medivac', 'CogBloomXT', 'NomNom2', 'AtomCrasher', 'Aegis', 'Clippy')
out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P(__doc__)
for A in FOCUS:
    opp = sorted({b for (a, b) in games if a == A}, key=lambda b: -len(games[(A, b)]))
    if not opp:
        continue
    P('\n## %s' % A)
    P('%-14s %4s %-3s | %-24s | %-24s | %-24s | %-24s' % ('vs', 'gms', 'win', 'fresh: n A%/B%', 'A armed: n A%/B%',
                                                        'B armed: n A%/B%', 'both: n A%/B%'))
    for B in opp:
        if len(games[(A, B)]) < 2:
            continue
        for w in ('a', 'b', 'all'):
            cells = []
            tot = 0
            for st in ('fresh', 'A armed', 'B armed', 'both'):
                c = C[(A, B, w, st)]
                t = sum(c.values())
                tot += t
                cells.append('%7d %5.1f/%5.1f' % (t, 100 * c['A'] / t, 100 * c['B'] / t) if t else '%7d     -/-    ' % 0)
            if tot:
                P('%-14s %4d %-3s | %s' % (B, len(games[(A, B)]), w, ' | '.join('%-24s' % s for s in cells)))
out.close()
