"""Naive baseline: the cell with the highest pre-match ladder rating (match page) wins.  Compared with the real winner
(largest final population, as validate.winner).  Also the sim winner rate from the pad3 / default runs and Wilson 95%."""
import json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate as V

D = os.path.join(V.ROOT, 'data')
nm = lambda s: re.sub(r'^\W+\s*', '', s).strip()
pre = {}
for f in ('pull2/other-match-pages.json', 'pull2/sprint-match-pages.json'):
    for k, p in json.load(open(os.path.join(D, f), encoding='utf-8'))['pages'].items():
        if p and p.get('rows'):
            pre[int(k)] = {nm(r[1]): int(re.findall(r'\d+', r[9])[0]) for r in p['rows']}
import glob
for f in glob.glob(os.path.join(D, 'pull2', 'summaries', '[0-9]*.json')):
    d = json.load(open(f, encoding='utf-8'))
    pre.setdefault(int(d['id']), {nm(r['cell']): int(re.findall(r'\d+', r['rating'])[0]) for r in d['facts']['rows']})
for f in ('pull3/matches-scourge-2026-11-08.json', 'pull4/matches-contagion-2026-11-08.json'):
    for m in json.load(open(os.path.join(D, f), encoding='utf-8'))['matches']:
        pre.setdefault(m['id'], {nm(c['name']): int(re.findall(r'\d+', c['rating'])[0]) for c in m['colonies']})


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return '%d/%d = %.0f%% (95%% %.0f-%.0f%%)' % (k, n, 100 * p, 100 * (c - h), 100 * (c + h))


t = V.load_table()
fit, test = V.split_sets(t)
miss = [m for m in t if m not in pre]
print('matches without a match page:', miss)
real = {m: V.cells_of(t, m)[V.winner(t[m]['rows'])] for m in t}
base = {m: max(pre[m], key=pre[m].get) for m in t if m in pre}
win = lambda p: max(range(4), key=lambda c: p[c])
import collections
wins = collections.Counter(real.values())
games = collections.Counter(n for m in t for n in V.cells_of(t, m))
mostwin = {m: max(V.cells_of(t, m), key=lambda n: (wins[n] / games[n], n)) for m in t}   # best real win share
for label, ids in (('FIT', fit), ('TEST', test)):
    print('win-share baseline %-4s %s' % (label, wilson(sum(mostwin[m] == real[m] for m in ids), len(ids))))
for tag in sys.argv[1:] or ['pad3', 'def']:
    sim = {}
    for s in ('fit', 'test'):
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 's63-%s-%s.json' % (tag, s))
        if os.path.exists(fn):
            for m, v in json.load(open(fn)).items():
                sim[int(m)] = v['names'][win([v['sim'][str(c)]['pend'] for c in range(4)])]
    for label, ids in (('FIT', fit), ('TEST', test)):
        ids_b = [m for m in ids if m in base]
        print('%s %-4s baseline %s   sim %s' % (tag, label, wilson(sum(base[m] == real[m] for m in ids_b), len(ids_b)),
              wilson(sum(sim[m] == real[m] for m in ids if m in sim), len([m for m in ids if m in sim]))
              if any(m in sim for m in ids) else '-'))
