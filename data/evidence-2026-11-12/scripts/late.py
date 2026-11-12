"""Scratch: our cell's lead over the best rival at t60 / t100 / t200 / t500 and the final result.
'Ahead then lost' games = the late-game pattern.  Usage: python late.py <review csv> [...]"""
import csv
import sys
from collections import defaultdict

rows = []
for f in sys.argv[1:]:
    rows += list(csv.DictReader(open(f, encoding='utf-8')))
by = defaultdict(dict)
for r in rows:
    by[r['replay']][r['name']] = r


def label(n, rid):
    if not n.startswith('Bane'):
        return n
    rid = int(rid)
    return 'Bane v1' if rid < 124690 else 'Bane v2.0' if rid < 126000 else 'Bane v2.1' if rid < 127810 else 'Bane v2.2'


OURS = ('Bane', 'Conviction', 'Penalty')
stat = defaultdict(lambda: defaultdict(int))
lines = []
for rid, rs in sorted(by.items()):
    ours = [r for n, r in rs.items() if n.startswith(OURS)]
    if len(ours) != 1:
        continue
    me = ours[0]
    nm = label(me['name'], rid)
    if nm == 'Bane v1':
        continue
    riv = max((r for r in rs.values() if r is not me), key=lambda r: int(r['final']))
    won = int(me['final']) > int(riv['final'])
    lead = {t: int(me['p%d' % t]) - int(riv['p%d' % t]) for t in (60, 100, 200, 500)}
    s = stat[nm.split(' v')[0] if nm.startswith('Bane') else nm]
    s['games'] += 1
    s['won'] += won
    for t in (60, 100, 200):
        if lead[t] > 0:
            s['ahead%d' % t] += 1
            s['ahead%d_lost' % t] += not won
    if lead[100] > 0 and not won:
        lines.append('%s %-11s ahead at t100 by %5d, t200 %5d, t500 %5d; final %4s v %4s %s' % (
            rid, nm, lead[100], lead[200], lead[500], me['final'], riv['final'], riv['name']))
for k, s in stat.items():
    print('%-11s games %3d won %3d | ahead@60 %3d (lost %2d) | ahead@100 %3d (lost %2d) | ahead@200 %3d (lost %2d)' % (
        k, s['games'], s['won'], s['ahead60'], s['ahead60_lost'], s['ahead100'], s['ahead100_lost'], s['ahead200'],
        s['ahead200_lost']))
print('\n'.join(lines))
