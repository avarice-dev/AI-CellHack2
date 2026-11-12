"""Scratch: pool blind.csv per cell.  Usage: python blind_sum.py <out.txt> <blind.csv>
empty-test: the square this cell bit last tick is empty now, another enemy is on an edge, the cell is not stunned:
  what it does (eat = bit the other enemy, none = no event, split).  'self' = the last target died to this cell's own
  bite, 'other' = it died to another cell's bite.  A checked repeat (or a scan) eats in both cases; a blind repeat
  shows 'none' at least when the cell expected the target to live ('other').
refill-test: the square holds a new enemy child (a refill): eats again at once (%).
refills: squares freed by this cell's kills that the dead cell's colony refilled: n, child bitten by the killer on its
  first live tick (%), killer bites per child, mean child birth energy, child dead within 5 ticks (%).
"""
import collections
import csv
import sys


def label(n, rid):
    if n != 'Bane':
        return n
    rid = int(rid)
    return 'Bane v1' if rid < 124690 else 'Bane v2.0' if rid < 126000 else 'Bane v2.1' if rid < 127810 else 'Bane v2.2'


NORM = {'Bane v2': 'Bane v2.0', 'CogSpore - VarSi': 'VarSi', 'CogSpore-Siect-F': 'Siect-F', 'CogBloomXT v4': 'CogBloomXT'}
rows = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
C = collections.defaultdict(collections.Counter)
G = collections.defaultdict(set)
for r in rows:
    n = r['name']
    n = n[:-2] if n.endswith((' W', ' L')) else n
    n = NORM.get(label(n, r['replay']), label(n, r['replay']))
    C[n][r['measure']] += int(r['n'])
    G[n].add(r['replay'])
out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P(__doc__)
pc = lambda a, b: '%5.1f' % (100 * a / b) if b else '    -'
for n in sorted(G, key=lambda n: -len(G[n])):
    c = C[n]
    if len(G[n]) < 3:
        continue
    parts = []
    for w in ('self', 'other'):
        t = c['blind_empty_%s_n' % w]
        parts.append('%s n %6d eat %s none %s split %s' % (w, t, pc(c['blind_empty_%s_eat' % w], t),
                                                           pc(c['blind_empty_%s_none' % w], t),
                                                           pc(c['blind_empty_%s_split' % w], t)))
    rn = c['refill_n']
    P('%-14s g%-3d %s | refill-test n %6d eat %s | refills n %6d first-tick %s bites/child %4.1f child e %4.1f '
      'dead5 %s' % (n, len(G[n]), ' | '.join(parts), c['blind_refill_n'], pc(c['blind_refill_eat'], c['blind_refill_n']),
                    rn, pc(c['refill_bit_first_tick'], rn), c['refill_killer_bites'] / rn if rn else 0,
                    c['refill_child_energy'] / rn if rn else 0, pc(c['refill_dead5'], rn)))
out.close()
