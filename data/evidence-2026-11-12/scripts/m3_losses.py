"""Scratch: measure 3 (review order): Bane v2.2 losses by winner, counts only, from the site match list.
Bane v2.2 = games with id >= 127810 (v2.1/v2.2 boundary).  'own' = another of our cells (Conviction, Penalty,
Schism, Pestilence) in the game.  Per rival: games with it present, its wins, our wins, other wins.
Usage: python m3_losses.py <ourmatches.json> > out.txt
"""
import collections
import json
import sys

OWN = ('Conviction', 'Penalty', 'Schism', 'Pestilence', 'Contagion')


def nm(s):
    return s.split(' ', 1)[-1] if s and not s[:1].isalnum() else s


rows = json.load(open(sys.argv[1], encoding='utf-8'))['rows']
g = [r for r in rows if r['id'] >= 127810 and r['status'] == 'done' and any(nm(c) == 'Bane' for c in r['colonies'])]
print('Bane v2.2 games %d-%d: %d' % (min(r['id'] for r in g), max(r['id'] for r in g), len(g)))
for label, sel in (('all', g), ('no other own cell', [r for r in g if not any(nm(c) in OWN for c in r['colonies'])]),
                   ('with another own cell', [r for r in g if any(nm(c) in OWN for c in r['colonies'])])):
    won = sum(nm(r['winner']) == 'Bane' for r in sel)
    by = collections.Counter(nm(r['winner']) for r in sel if nm(r['winner']) != 'Bane')
    print('\n## %s: %d games, Bane won %d (%.1f%%), lost %d' % (label, len(sel), won, 100.0 * won / max(len(sel), 1), len(sel) - won))
    print('losses by winner:', ', '.join('%s %d' % kv for kv in by.most_common()))
    pres = collections.Counter()
    rw = collections.Counter()
    bw = collections.Counter()
    for r in sel:
        for c in set(nm(c) for c in r['colonies']) - {'Bane'}:
            pres[c] += 1
            rw[c] += nm(r['winner']) == c
            bw[c] += nm(r['winner']) == 'Bane'
    print('rival present: games | rival won | Bane won | someone else won')
    for c, n in pres.most_common():
        if n >= 5 or rw[c]:
            print('  %-14s %4d | %4d | %4d | %4d' % (c, n, rw[c], bw[c], n - rw[c] - bw[c]))

# Addendum: Bane games after the list (id > max) from pull9 match pages (a picked sample, not consecutive: listed only)
if len(sys.argv) > 2:
    top = max(r['id'] for r in g)
    ms = json.load(open(sys.argv[2], encoding='utf-8'))['matches']
    late = sorted((m for m in ms if m['id'] > top and any(nm(c) == 'Bane' for c in m['cells'])), key=lambda m: m['id'])
    print('\n## after %d (pull9 match pages, picked sample, not consecutive): %d Bane games' % (top, len(late)))
    for m in late:
        print('  %d winner %-18s | %s' % (m['id'], nm(m['winner']), ', '.join(nm(c) for c in m['cells'])))
