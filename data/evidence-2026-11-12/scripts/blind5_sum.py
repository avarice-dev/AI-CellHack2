"""Scratch: measure 5 summary from blind.py r5x rows (review 2026-11-12).
Per killer (Bane v2.2 = ids >= 127810; main rivals pooled by name): the killer's action on t1 (the refill child's first
live tick) by its action on t0 and by its enemy edge neighbours at the start of t0 (0 / 1 / 2+); Bane also per
refilling-colony group.  Key cell: P(eat-child on t1 | t0 = none).  'free' = t0 none and not stunned by another
enemy on t1 (review's decision rule).
Usage: python blind5_sum.py <blind.csv> > out.txt
"""
import collections
import csv
import sys

T1 = ('eat-child', 'eat-same', 'eat-new', 'stunned-child', 'stunned-other', 'split', 'move', 'feed', 'none', 'dead',
      'child-dead', 'unknown', 'eat-friend')


def killer(r):
    n = r['name']
    if n.startswith('Bane'):
        return 'Bane v2.2' if int(r['replay']) >= 127810 else None
    for k in ('Siect-F', 'VarSi', 'CogSpore', 'CogBloomXT', 'Colossus', 'medivac', 'NomNom2', 'Conviction', 'Penalty'):
        if k in n:
            return 'CogSpore' if n.endswith('CogSpore') else k
    return None


def group(name):
    return 'Siect-F' if 'Siect' in name else 'Yen' if ('VarSi' in name or 'Cog' in name or 'Clippy' in name) else \
        'feeder' if any(k in name for k in ('Colossus', 'medivac', 'NomNom2')) else 'own' if any(
            k in name for k in ('Conviction', 'Penalty', 'Schism', 'Pestilence')) else 'other'


c = collections.Counter()
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8')):
    if not r['measure'].startswith('r5x|'):
        continue
    k = killer(r)
    if k is None:
        continue
    _, a0, a1, nb, w, ref = r['measure'].split('|', 5)
    n = int(r['n'])
    for g in ('all', group(ref)) if k == 'Bane v2.2' else ('all',):
        for key in ((k, g, 'all', 'all'), (k, g, 't0=' + a0, 'all'), (k, g, 'all', 'nb=' + nb), (k, g, 't0=' + a0, 'nb=' + nb)):
            c[key + ('n',)] += n
            c[key + (a1,)] += n


def line(key):
    n = c[key + ('n',)]
    free = c[key + ('n',)] - c[key + ('stunned-other',)]
    return '%-11s %-7s %-12s %-6s %6d | %s | free %5d: eat-child %5.1f%%' % (
        key + (n, ' '.join('%5.1f' % (100.0 * c[key + (a,)] / n) for a in T1), free,
        100.0 * c[key + ('eat-child',)] / free if free else 0))


print('killer      refill  t0           nbrs        n | t1 %: ' + ' '.join('%5s' % a[:5] for a in T1))
print('(t1 columns: ' + ', '.join(T1) + ')')
keys = sorted(set(k[:4] for k in c))
for k in keys:
    if c[k + ('n',)] >= 30 and (k[1] == 'all' or k[2:] == ('all', 'all') or k[2] == 't0=none'):
        print(line(k))
