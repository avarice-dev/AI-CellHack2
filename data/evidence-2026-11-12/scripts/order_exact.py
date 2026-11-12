"""Scratch: exact rival bite-cost classes from order.csv (lo = largest marker cost before the eat in that tick,
hi = smallest after).  Ties are a seeded coin, so a rival eat of cost exactly X lands BETWEEN our cost-X markers
(lo = hi = X) whenever the tick has several of them.  Classes:
  v2.1/v2.2 games (markers 4, 16, 39):  <4 (hi = 4, lo < 4) | =4 (lo = hi = 4) | 5-15 (lo = 4, hi = 16) |
      =16 (lo = hi = 16) | 17-38 (lo = 16, hi = 39) | other (no marker on one side or wider bracket)
  v1/v2.0 games (markers 5, 11):  <5 | =5 | 6-10 | =11 | >11 | other
Usage: python order_exact.py <out.txt> <order.csv>
"""
import collections
import csv
import sys

NORM = {'CogSpore - VarSi': 'VarSi', 'CogSpore-Siect-F': 'Siect-F', 'CogBloomXT v4': 'CogBloomXT'}


def cls(eg, lo, hi):
    if eg == 'new':
        if hi == 4 and lo < 4:
            return '<4'
        if lo == 4 and hi == 4:
            return '=4'
        if lo == 4 and hi == 16:
            return '5-15'
        if lo == 16 and hi == 16:
            return '=16'
        if lo == 16 and hi == 39:
            return '17-38'
        if lo == 39:
            return '>=39'
        return 'other'
    if hi == 5 and lo < 5:
        return '<5'
    if lo == 5 and hi == 5:
        return '=5'
    if lo == 5 and hi == 11:
        return '6-10'
    if lo == 11 and hi == 11:
        return '=11'
    if lo == 11:
        return '>11'
    return 'other'


CL = {'new': ('<4', '=4', '5-15', '=16', '17-38', '>=39', 'other'), 'old': ('<5', '=5', '6-10', '=11', '>11', 'other')}
rows = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
C = collections.defaultdict(collections.Counter)
G = collections.defaultdict(set)
for r in rows:
    if r['rival'] == '_check' or r['target'] == 'other':
        continue
    eras = r['era'].split('+')
    if 'v2.1' in eras or 'v2.2' in eras:
        eg = 'new'
    elif 'v2.0' in eras or 'v1' in eras:
        eg = 'old'
    else:
        continue
    rv = NORM.get(r['rival'], r['rival'])
    k = cls(eg, int(r['lo']), int(r['hi']))
    for w in (r['window'], 'all'):
        C[(rv, eg, r['kind'], w)][k] += int(r['n'])
    G[(rv, eg)].add(r['replay'])
out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P(__doc__)
for eg, title in (('new', 'Bane v2.1 / v2.2 games: our bites 4 (repeat) / 16 (first)'),
                  ('old', 'Bane v1 / v2.0 games: our bites 5 (all)')):
    P('\n## %s.  Share of the rival\'s eats on our cells by exact cost class' % title)
    P('%-14s %-6s %-3s %8s | %s' % ('rival', 'kind', 'w', 'eats', ' '.join('%6s' % c for c in CL[eg])))
    rv_all = sorted({k[0] for k in C if k[1] == eg}, key=lambda v: -sum(C[(v, eg, kk, 'all')].total()
                                                                        for kk in ('first', 'repeat')))
    for rv in rv_all:
        for kind in ('first', 'repeat'):
            for w in ('a', 'b'):
                c = C.get((rv, eg, kind, w))
                if not c or c.total() < 100:
                    continue
                t = c.total()
                P('%-14s %-6s %-3s %8d | %s   (%d games)' % (rv, kind, w, t, ' '.join(
                    '%6.1f' % (100 * c[k] / t) for k in CL[eg]), len(G[(rv, eg)])))
out.close()
