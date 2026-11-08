"""Aggregate data/pull2/summaries/[0-9]*.json into markdown tables (stdout).
Run from the project root: python -I tools/pull2/report.py [dir|fp|starts|rules|val|all]
History: reproduces our pull 2 report (data/ladder-data-2-2026-11-08.md); reads only data/pull2 in the pull 2 formats."""
import json, glob, re, sys, collections

S = {}
for f in sorted(glob.glob('data/pull2/summaries/[0-9]*.json')):
    d = json.load(open(f, encoding='utf-8'))
    S[d['id']] = d


def nm(s):
    return re.sub(r'^\W+\s*', '', s).strip()


def cells(d):
    return [nm(r['cell']) for r in d['facts']['rows']]


DIRS = ['UP', 'RIGHT', 'DOWN', 'LEFT']


def reading(p, n):
    if n < 50:
        return '?'
    if p >= 90:
        return '<=5'
    if 30 <= p <= 80:
        return '6'
    if p <= 10:
        return '>=7'
    return '5-7?'


def sec_dir():
    agg = collections.defaultdict(lambda: {d: [0.0, 0] for d in DIRS})
    per = collections.defaultdict(list)
    for id_, d in S.items():
        cs = cells(d)
        if 'Sprint' not in cs:
            continue
        s = cs.index('Sprint')
        for a, c in enumerate(cs):
            if a == s:
                continue
            b = d['biteFirst'].get('%d>%d' % (a, s), {})
            row = {}
            for dr in DIRS:
                r = b.get(dr)
                if r and r['n']:
                    first = r['pre'] + r['mixFirst']
                    row[dr] = (100 * first / r['n'], r['n'])
                    agg[c][dr][0] += first
                    agg[c][dr][1] += r['n']
            if row:
                per[c].append((id_, row))
    print('| Rival | UP | RIGHT | DOWN | LEFT | reading |\n|---|---|---|---|---|---|')
    for c in sorted(agg, key=lambda c: -sum(v[1] for v in agg[c].values())):
        cols, rd = [], []
        for dr in DIRS:
            f, n = agg[c][dr]
            if n:
                p = 100 * f / n
                cols.append('%.0f%% n%d' % (p, n))
                rd.append(dr[0] + ':' + reading(p, n))
            else:
                cols.append('-')
                rd.append(dr[0] + ':-')
        print('| %s (pooled) | %s | %s |' % (c, ' | '.join(cols), ' '.join(rd)))
    print('\nPer replay:')
    for c in sorted(per):
        for id_, row in per[c]:
            print('  %s %d: %s' % (c, id_, ' '.join('%s %.0f%%/n%d' % (dr[0], row[dr][0], row[dr][1]) for dr in DIRS if dr in row)))


def sec_val():
    print('| match | colony | pop t50 | t100 | t200 | t500 | t1000 | end | E t200 | E t1000 | feeds/eat | freeze |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for id_, d in S.items():
        cs = cells(d)
        for c in range(4):
            p = d['pop10'][c]
            g = lambda t: p[t // 10] if t // 10 < len(p) else '-'
            me = d['meanEnergy']
            e = lambda t: me[str(t)][c] if str(t) in me else None
            print('| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                id_, cs[c], g(50), g(100), g(200), g(500), g(1000), d['popFinal'][c], e(200), e(1000),
                d['feed'][c]['feedsPerEat'], d['freezeTick']))


def sec_starts():
    ne, md = [], []
    print('Starts (x,y per colony):')
    for id_, d in S.items():
        cs = cells(d)
        print('  %d: %s' % (id_, '; '.join('%s (%d,%d)' % (cs[c], d['starts'][c][0]['x'], d['starts'][c][0]['y'])
                                           for c in range(4) if d['starts'][c])))
        for c in range(4):
            if d['starts'][c]:
                ne.append(d['starts'][c][0]['nearestEdge'])
        md.append(min(p['manhattan'] for p in d['startPairs']))

    def hist(a, w):
        h = collections.Counter(x // w * w for x in a)
        return ', '.join('%d-%d: %d' % (k, k + w - 1, h[k]) for k in sorted(h))
    print('nearest-edge distance (n=%d): min %d median %d max %d | %s' % (len(ne), min(ne), sorted(ne)[len(ne) // 2], max(ne), hist(ne, 5)))
    print('min Manhattan distance between starts per match (n=%d): min %d median %d max %d | %s' % (len(md), min(md), sorted(md)[len(md) // 2], max(md), hist(md, 10)))


def sec_rules():
    tr = collections.Counter(); eat = collections.Counter(); feed = collections.Counter()
    dh = [collections.Counter() for _ in range(6)]
    for d in S.values():
        for c in range(4):
            for k, v in d['split'][c]['triples'].items():
                tr[k] += v
            for k, v in d['eatAmtHist'][c].items():
                eat[k] += v
            for k, v in d['feed'][c]['feedAmtHist'].items():
                feed[k] += v
        for r, h in enumerate(d.get('deltaHist', [])):
            for k, v in h.items():
                dh[r][k] += v
    print('eat amounts:', dict(eat.most_common(6)))
    print('feed amounts:', dict(feed.most_common(6)))
    odd = collections.Counter(); even = collections.Counter(); bad = 0
    for k, v in tr.items():
        b, c, a = map(int, k.split(','))
        if b % 2:
            odd[(c == b // 2 and a == b - c)] += v
        else:
            even[(c == a == b // 2)] += v
        if b != c + a:
            bad += v
    print('odd parent energy, child=floor(b/2) and parent=rest:', dict(odd), '| even halves:', dict(even), '| before != child+after:', bad)
    print('top split triples (before,child,after):', tr.most_common(12))
    names = ['untouched', 'eater (1 event)', 'target (1 event)', 'feeder (1 event)', 'receiver (1 event)', 'several events']
    for r in range(6):
        print('delta', names[r], ':', dict(dh[r].most_common(6)))


def sec_fp():
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for id_, d in S.items():
        cs = cells(d)
        for c in range(4):
            v = by[cs[c]]
            v['id'].append(id_)
            sp = d['split'][c]
            if sp['attributed'] > 100:
                v['pb'].append({int(k): n for k, n in sp['parentBefore'].items()})
            v['feeds'].append(d['totals'][c]['feeds']); v['eats'].append(d['totals'][c]['eatsEnemy'])
            t = d['totals'][c]
            v['moves'].append(t['moves'])
            fi = d['frontInterior']
            for tt in ('500', '1000'):
                if tt in fi and fi[tt][c]['front']['n']:
                    v['front' + tt].append(fi[tt][c]['front']['mean'])
                    v['int' + tt].append(fi[tt][c]['interior']['mean'] if fi[tt][c]['interior']['n'] else 0)
            v['insns'].append(d['facts']['rows'][c]['insns'])
    mean = lambda a: ('%.1f' % (sum(a) / len(a))) if a else '-'
    for c, v in sorted(by.items()):
        pbs = collections.Counter()
        for pb in v['pb']:
            for k, n in pb.items():
                pbs[k] += n
        tot = sum(pbs.values())
        thr = ', '.join('%d:%.0f%%' % (k, 100 * n / tot) for k, n in pbs.most_common(4)) if tot else '-'
        print('%s (n=%d): parent energy before split top: %s; min seen %s; feeds/eat pooled %s; moves %d; front/interior @500 %s/%s @1000 %s/%s; insns %s' % (
            c, len(v['id']), thr, min(pbs) if pbs else '-', ('%.1f' % (sum(v['feeds']) / max(1, sum(v['eats'])))), sum(v['moves']),
            mean(v['front500']), mean(v['int500']), mean(v['front1000']), mean(v['int1000']), ' '.join(sorted(set(v['insns']))[:4])))


if __name__ == '__main__':
    w = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for n, f in (('dir', sec_dir), ('fp', sec_fp), ('starts', sec_starts), ('rules', sec_rules), ('val', sec_val)):
        if w in ('all', n):
            print('\n### ' + n)
            f()
