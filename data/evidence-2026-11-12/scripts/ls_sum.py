"""Scratch: pool lost_squares.py CSVs per cell name (Bane labelled by id in names.json already).
Usage: python ls_sum.py <out.txt> <csv> [...]"""
import csv, sys, collections
rows = []
for f in sys.argv[2:]:
    rows += list(csv.DictReader(open(f, encoding='utf-8')))
def label(n, rid):
    """The site names every Bane version 'Bane': label by match id."""
    if n != 'Bane':
        return n
    rid = int(rid)
    return 'Bane v1' if rid < 124690 else 'Bane v2.0' if rid < 126000 else 'Bane v2.1' if rid < 127810 else 'Bane v2.2'
cnt = collections.defaultdict(collections.Counter)    # (name, window) -> counter
games = collections.defaultdict(set)
for r in rows:
    cnt[(label(r['name'], r['replay']), r['window'])][(r['result'], r['state'])] += int(r['n'])
    games[label(r['name'], r['replay'])].add(r['replay'])
out = open(sys.argv[1], 'w', encoding='utf-8')
def P(*a):
    print(*a, file=out)
names = sorted(games, key=lambda n: -len(games[n]))
P('# Contested empty squares per cell (pooled over games). won/lost/open = % of square-ticks where the cell had a neighbour.')
P('# lost-state = our best-placed neighbour on squares the cell lost (% of lost). fills: child/mover energy, alive10, held10.')
for n in names:
    if len(games[n]) < 3:
        continue
    for w in 'abc':
        c = cnt[(n, w)]
        tot = sum(v for (res, s), v in c.items() if res in ('won', 'lost', 'open'))
        if not tot:
            continue
        won = sum(v for (res, s), v in c.items() if res == 'won')
        lost = sum(v for (res, s), v in c.items() if res == 'lost')
        ls = {s: v for (res, s), v in c.items() if res == 'lost'}
        lsx = ' '.join('%s %.0f' % (s, 100 * v / lost) for s, v in sorted(ls.items(), key=lambda t: -t[1])) if lost else ''
        fills = collections.defaultdict(dict)
        for (res, s), v in c.items():
            if res.startswith('fill-'):
                k, m = res.split(':')
                fills[(k[5:], s)][m] = v
        fx = []
        for (k, s), d in sorted(fills.items()):
            if d.get('n', 0) >= 20:
                fx.append('%s %s n%d a%.0f h%.0f' % (k, s, d['n'], 100 * d.get('alive10', 0) / d['n'], 100 * d.get('held10', 0) / d['n']))
        P('%-20s g%-3d %s  sq %6d won %4.1f lost %4.1f | lost-state: %s' % (n[:20], len(games[n]), w, tot, 100 * won / tot, 100 * lost / tot, lsx))
        P('%27s fills: %s' % ('', '; '.join(fx)))
out.close()
