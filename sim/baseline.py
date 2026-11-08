"""Naive baseline (every data pull): the cell with the highest pre-match ladder rating (match page) wins.  Compared with the real winner
(largest final population, as validate.winner).  Also the sim winner rate from the pad3 / default runs and Wilson 95%."""
import json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate as V

nm = lambda s: re.sub(r'^\W+\s*', '', s).strip()
pre = {}
import glob
# Pre-match ratings from every data pull (validate.pulls()): saved match pages (*match-pages.json, pull 2 format),
# summaries/<id>.json (pull 2 format), and match lists (matches-*.json) whose matches carry 'colonies'.
for p in V.pulls():
    d = os.path.join(V.DATA, p)
    for f in sorted(glob.glob(os.path.join(d, '*match-pages.json'))):
        for k, pg in json.load(open(f, encoding='utf-8'))['pages'].items():
            if pg and pg.get('rows'):
                pre.setdefault(int(k), {nm(r[1]): int(re.findall(r'\d+', r[9])[0]) for r in pg['rows']})
    for f in glob.glob(os.path.join(d, 'summaries', '[0-9]*.json')):
        s = json.load(open(f, encoding='utf-8'))
        pre.setdefault(int(s['id']), {nm(r['cell']): int(re.findall(r'\d+', r['rating'])[0]) for r in s['facts']['rows']})
    for f in sorted(glob.glob(os.path.join(d, 'matches-*.json'))):
        for m in json.load(open(f, encoding='utf-8'))['matches']:
            if m.get('colonies'):
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
