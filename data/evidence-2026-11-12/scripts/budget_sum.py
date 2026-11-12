"""Scratch: pool budget.py rows per cell name and window.  Usage: python budget_sum.py <out.txt> <budget.csv>
Windows: a t0-30, b 30-60, c 60-100, d 100-200, e 200+ ('near' not computed from t300).
Per cell and window: cell-ticks; action shares; energy shares; then three situations:
  front (enemy on an edge), near (enemy in the 5x5, not on an edge), far (no enemy in the 5x5),
each: share of cell-ticks, action shares within it, and idle-with-space (no event, an empty edge, energy >= 5).
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
C = collections.defaultdict(collections.Counter)
games = collections.defaultdict(set)
for r in rows:
    n = label(r['name'], r['replay'])
    C[(n, r['window'])][(r['act'], r['space'], r['enemy'], r['energy'])] += int(r['n'])
    games[n].add(r['replay'])
ACTS = ('split', 'move', 'feed', 'eat', 'stunned', 'none')
EN = ('<5', '5-11', '12-15', '16-49', '50')
out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P(__doc__)
for n in sorted(games, key=lambda n: -len(games[n])):
    if len(games[n]) < 3:
        continue
    P('\n## %s (%d games)' % (n, len(games[n])))
    for w in 'abcde':
        c = C[(n, w)]
        tot = sum(c.values())
        if not tot:
            continue
        a = collections.Counter()
        e = collections.Counter()
        for (act, sp, en_, eb), v in c.items():
            a[act] += v
            e[eb] += v
        P('%s cell-ticks %9d | %s | energy %s' % (w, tot, ' '.join('%s %4.1f' % (k, 100 * a[k] / tot) for k in ACTS),
                                                  ' '.join('%s %4.1f' % (k, 100 * e[k] / tot) for k in EN)))
        for sit in ('front', 'near', 'far'):
            s = {k: v for k, v in c.items() if k[2] == sit}
            st = sum(s.values())
            if not st:
                continue
            sa = collections.Counter()
            idle = 0
            idle_e = collections.Counter()
            opn = 0
            for (act, sp, en_, eb), v in s.items():
                sa[act] += v
                if sp == 'open':
                    opn += v
                    if act == 'none' and eb != '<5':
                        idle += v
                        idle_e[eb] += v
            P('   %-5s %5.1f%% of ticks, open %5.1f%% | %s | idle-with-space %4.1f%% (%s)' % (
                sit, 100 * st / tot, 100 * opn / st, ' '.join('%s %4.1f' % (k, 100 * sa[k] / st) for k in ACTS),
                100 * idle / st, ' '.join('%s %.1f' % (k, 100 * v / st) for k, v in sorted(idle_e.items()))))
out.close()
