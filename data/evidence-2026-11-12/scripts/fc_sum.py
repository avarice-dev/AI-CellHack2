"""Scratch: review R1 summary of first_contact.csv (Bane v2.2 new edge pairs).
Tables: (1) who entered, by rival group and window: n, we / enemy / neither %, dead 5 / 10 %, first-order flips if our
bite cost 4 (as % of n); (2) enemy entered: by our state on the previous tick x other enemy on an edge; gate first
choice share; (3) our newborn entered: by parent rule x inherited lock x place; (4) enemy-first by cost class and
direction.
Usage: python fc_sum.py <first_contact.csv> > out.txt
"""
import collections
import csv
import sys


def group(name):
    return 'Siect-F' if 'Siect' in name else 'Yen' if ('VarSi' in name or 'Cog' in name or 'Clippy' in name) else \
        'feeder' if any(k in name for k in ('Colossus', 'medivac', 'NomNom2')) else 'own' if any(
            k in name for k in ('Conviction', 'Penalty')) else 'other'


rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
GROUPS = ('all', 'Yen', 'Siect-F', 'feeder', 'other')


def table(title, keyf, filt=lambda r: True, minn=30):
    c = collections.Counter()
    for r in rows:
        if not filt(r):
            continue
        n = int(r['n'])
        for g in ('all', group(r['rival'])):
            for w in (r['window'], 'all'):
                k = (g, w) + keyf(r)
                c[k + ('n',)] += n
                c[k + (r['result'],)] += n
                c[k + ('d5',)] += n * int(r['d5'])
                c[k + ('d10',)] += n * int(r['d10'])
                if r['flip'] not in ('-', ''):
                    c[k + ('flip',)] += n * float(r['flip'])
    print('\n## %s' % title)
    print('group    w   key | n | we / enemy / neither % | dead 5 / 10 % | flips if our bite were 4 (% of n)')
    for k in sorted({k[:-1] for k in c}, key=lambda k: (GROUPS.index(k[0]) if k[0] in GROUPS else 9, k[1:])):
        n = c[k + ('n',)]
        if n < minn or k[0] not in GROUPS:
            continue
        print('%-8s %-3s %-40s %7d | %5.1f %5.1f %5.1f | %5.1f %5.1f | %5.1f' % (
            k[0], k[1], ' '.join(k[2:]), n, *(100.0 * c[k + (x,)] / n for x in ('we', 'enemy', 'neither', 'd5', 'd10', 'flip'))))


table('(1) who entered', lambda r: (r['entered'],))
table('(2) enemy entered: our state on the previous tick x other enemy on an edge (other=1)',
      lambda r: (r['prev'], 'other=' + r['other']), lambda r: r['entered'].startswith('enemy'))
table('(2b) enemy entered: X entered our gate first choice (gatech=1) x our previous state',
      lambda r: ('gatech=' + r['gatech'], r['prev']), lambda r: r['entered'].startswith('enemy'))
table('(3) our newborn entered: parent rule x inherited lock x enemy place',
      lambda r: (r['nbrule'], r['nblock'], r['nbplace']), lambda r: r['entered'] == 'our-split')
table('(4) enemy bit first: cost class x direction x our plan',
      lambda r: (r['ecost'], r['edir'], r['plan']), lambda r: r['result'] == 'enemy')
