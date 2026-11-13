"""Scratch (brief v2.3 section 2b): coverage of the part A rest-tail rule on enemy entries beside a Bane v2.2 cell that
rested on the previous tick, with no other enemy on an edge (first_contact.csv columns rs1 / rs2).
rs1 = refill pattern only (thr_tbl = 12); rs2 = the brief's precedence (refill pattern, else DOWN for view 22, else UP
for view 2).  Rows: hold and rest under 5 only.  'none-other' (no event, open, e >= 5, not a 5-11 hold) is left out:
it mixes holders at 12-15 with cells whose split or move failed, which never ran the rest tail.
Usage: python coverage.py <first_contact.csv> > out.txt
"""
import collections
import csv
import sys


def grp(n):
    return 'Siect-F' if 'Siect' in n else 'Yen' if ('VarSi' in n or 'Cog' in n or 'Clippy' in n) else \
        'feeder' if any(k in n for k in ('Colossus', 'medivac', 'NomNom2')) else 'other'


c = collections.Counter()
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8')):
    if r['rs1'] in ('-', '') or r['other'] != '0' or r['prev'] not in ('hold', 'rest<5'):
        continue
    n = int(r['n'])
    for g in ('all', grp(r['rival'])):
        k = (g, r['prev'])
        c[k + ('n',)] += n
        c[k + ('en',)] += n * (r['result'] == 'enemy')
        for f in ('rs1', 'rs2'):
            if r[f] == '1':
                c[k + (f,)] += n
                c[k + (f + 'en',)] += n * (r['result'] == 'enemy')
                c[k + (f + 'fl',)] += n * (float(r['flip']) if r['flip'] not in ('-', '') else 0)
print(__doc__.split('Usage')[0])
print('group    prev         n | covered rs1 / rs2 % | enemy first: all / among rs2-covered % | first-order flips rs1 / rs2 (% of n)')
for g in ('all', 'Yen', 'Siect-F', 'feeder', 'other'):
    for pv in ('hold', 'rest<5'):
        k = (g, pv)
        n = c[k + ('n',)]
        if n < 20:
            continue
        b = c[k + ('rs2',)]
        print('%-8s %-7s %6d | %5.1f / %5.1f | %5.1f / %5.1f | %5.1f / %5.1f' % (
            g, pv, n, 100.0 * c[k + ('rs1',)] / n, 100.0 * b / n, 100.0 * c[k + ('en',)] / n,
            100.0 * c[k + ('rs2en',)] / b if b else 0, 100.0 * c[k + ('rs1fl',)] / n, 100.0 * c[k + ('rs2fl',)] / n))
