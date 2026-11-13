"""Scratch: measure 7 (review): races of Bane v2.2 newborns (first live tick) vs older cells, by plan and rival group.
Plan lock = the stored bite (copied from the parent for a newborn) points at an enemy: 4 instructions; first =
bite_tbl scan: 16.  won = our cell bit its planned target first; lost = an enemy bit our cell first (stunned), split
into lost-to-target (plan) and lost-to-another (plan-other).  Windows: a t < 100, b later.
Usage: python newborn_sum.py <race.csv> > out.txt
"""
import collections
import csv
import sys


def group(name):
    return 'Siect-F' if 'Siect' in name else 'Yen' if ('VarSi' in name or 'Cog' in name or 'Clippy' in name) else \
        'feeder' if any(k in name for k in ('Colossus', 'medivac', 'NomNom2')) else 'own' if any(
            k in name for k in ('Conviction', 'Penalty')) else 'other'


c = collections.Counter()
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8')):
    if r['rival'] == '_check' or r['era'] != 'v2.2':
        continue
    base = r['plan'].replace('-other', '')
    res = 'won' if r['first'] == 'A' else 'lost-other' if r['plan'].endswith('-other') else 'lost'
    n = int(r['n'])
    for g in ('all', group(r['rival'])):
        for w in (r['window'], 'all'):
            c[(r['newborn'], base, g, w, res)] += n
print('Bane v2.2 races: newborn (1) vs older (0) | plan | rival group | window: n, won %, lost to target %, lost to another %')
for nb in ('1', '0'):
    for base in ('lock', 'first'):
        for g in ('all', 'Yen', 'Siect-F', 'feeder', 'other', 'own'):
            for w in ('all', 'a', 'b'):
                ks = [c[(nb, base, g, w, x)] for x in ('won', 'lost', 'lost-other')]
                n = sum(ks)
                if n >= 20:
                    print('newborn %s %-5s %-8s %-3s n %8d | won %5.1f | lost %5.1f | lost-other %5.1f' % (
                        nb, base, g, w, n, *(100.0 * k / n for k in ks)))
