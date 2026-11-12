"""Scratch: how far behind its own start's solo curve each of our colonies was, and why.
Usage: python start_gap.py <solo.csv> <review csv> [<review csv> ...]
Our colonies = names starting Bane / Conviction / Penalty (all share the v2.x opening; Bane v1 rows are skipped by
the version labels 'Bane v2', 'Bane v2.1', 'Bane v2.2', 'Bane', 'Bane L' etc. only when the start is in solo.csv).
Per game: real cells / solo cells at t30, t60, t100; contact share in t0-30 and t30-60; nearest other start;
the best rival's start (wall) and cells; final share.
"""
import csv
import sys
from collections import defaultdict

solo = {(int(r['x']), int(r['y'])): r for r in csv.DictReader(open(sys.argv[1]))}
rows = []
for f in sys.argv[2:]:
    rows += list(csv.DictReader(open(f, encoding='utf-8')))
OURS = ('Bane', 'Conviction', 'Penalty')


def version(name, rid):
    """The site names every Bane version 'Bane': label by match id (v1 = cell 272, first v2.0 game 124697,
    v2.1 = cell 287 from about 126000 (none pulled between 125043 and 126918), v2.2 = cell 289 from about 127810)."""
    if not name.startswith('Bane'):
        return name
    rid = int(rid)
    return 'Bane v1' if rid < 124690 else 'Bane v2.0' if rid < 126000 else 'Bane v2.1' if rid < 127810 else 'Bane v2.2'


by = defaultdict(list)
for r in rows:
    r['name'] = version(r['name'], r['replay'])
    by[r['replay']].append(r)
out = []
for rid, rs in by.items():
    tot = sum(int(r['final']) for r in rs) or 1
    for r in rs:
        r['share'] = int(r['final']) / tot
    for r in rs:
        if not r['name'].startswith(OURS) or r['name'].startswith('Bane v1'):
            continue
        s = solo.get((int(r['x']), int(r['y'])))
        if s is None:
            continue
        riv = max((o for o in rs if o is not r), key=lambda o: o['share'])
        ours_in = sum(1 for o in rs if o['name'].startswith(OURS))
        d = dict(replay=rid, name=r['name'], share=r['share'], wall=int(r['wall']), near=int(r['near']),
                 p30=int(r['p30']), p60=int(r['p60']), p100=int(r['p100']),
                 s30=int(s['s30']), s60=int(s['s60']), s100=int(s['s100']),
                 c0=float(r['t0_contact']), c30=float(r['t30_contact']), c60=float(r['t60_contact']),
                 h30=float(r['t30_hold']), f30=float(r['t30_feed']), f60=float(r['t60_feed']),
                 bf60=float(r['t60_bitfirst']), d30=int(r['t30_deaths']), d60=int(r['t60_deaths']),
                 riv=riv['name'], rshare=riv['share'], rwall=int(riv['wall']), rnear=int(riv['near']),
                 r60=int(riv['p60']), r100=int(riv['p100']), ours=ours_in)
        d['g30'], d['g60'], d['g100'] = d['p30'] / d['s30'], d['p60'] / d['s60'], d['p100'] / d['s100']
        out.append(d)
out.sort(key=lambda d: d['g60'])
hdr = ('replay', 'name', 'share', 'wall', 'near', 'p60', 's60', 'g30', 'g60', 'g100', 'c0', 'c30', 'c60', 'h30',
       'f60', 'bf60', 'd60', 'riv', 'rshare', 'rwall', 'r60', 'r100', 'ours')
print(' '.join('%8s' % h[:8] for h in hdr))
for d in out:
    print(' '.join(('%8.2f' % d[h]) if isinstance(d[h], float) else ('%8s' % str(d[h])[:8]) for h in hdr))
if len(sys.argv) > 2 and out:
    with open('start_gap_out.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
