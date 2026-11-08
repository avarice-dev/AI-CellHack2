"""Late-game "treadmill" metrics, real replays vs sim (targets from data/scourge-losses-2026-11-08.md).

Per colony, from the race rows (one per death; Engine(record_races=True).race_rows() or
data/pull2/mining/races/<id>.csv.gz) and the population every 10 ticks:
  deaths per tick in each window (t < 500, 500-1000, >= 1000),
  own-refill share: of the colony's death squares that were refilled, the share it refilled itself,
  contested races vs each opponent: deaths of either colony with both adjacent, won by this colony,
  population change t500 -> end (fraction of t500), first tick at pop 128 and 512 (10-tick resolution).

  python treadmill.py --set fit --workers 2        # sim vs real over the FIT matches
  python treadmill.py --set test                   # judge only
  python treadmill.py --set fit --rpump-refill 1   # any engine / model option of validate.py
"""

import argparse
import csv
import gzip
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACES = os.path.join(ROOT, 'data', 'pull2', 'mining', 'races')
SUMS = os.path.join(ROOT, 'data', 'pull2', 'summaries')
WIN = ((0, 500), (500, 1000), (1000, 10 ** 9))


def window(t):
    return 0 if t < 500 else 1 if t < 1000 else 2


def metrics(rows, pop10, ncol=4):
    """rows: (tDeath, deadCol, killerCol, contMask, fillCol, dt, fillKind, fillE); pop10[k][c] = pop at
    tick 10k.  Returns {c: {...}} (JSON-able, counts so that matches can be pooled)."""
    ticks = 10 * (len(pop10) - 1)
    out = {}
    for c in range(ncol):
        out[c] = {'deaths': [0, 0, 0], 'filled': [0, 0, 0], 'own': [0, 0, 0],
                  'cont': {}, 'killed_by': {}, 'span': [max(0, min(hi, ticks) - lo) for lo, hi in WIN]}
    for t, dc, kc, mask, fc, dt, kind, fe in rows:
        w = window(t)
        if 0 <= dc < ncol:
            o = out[dc]
            o['deaths'][w] += 1
            kb = o['killed_by'].setdefault(str(kc), [0, 0, 0])
            kb[w] += 1
            if fc >= 0:
                o['filled'][w] += 1
                o['own'][w] += fc == dc
        for c in range(ncol):
            if not mask >> c & 1:
                continue
            for b in range(ncol):
                if b == c or not mask >> b & 1 or dc not in (b, c):
                    continue
                k = out[c]['cont'].setdefault(str(b), [[0, 0], [0, 0], [0, 0]])
                k[w][0] += 1
                k[w][1] += fc == c
    for c in range(ncol):
        ps = [p[c] for p in pop10]
        p500 = ps[50] if len(ps) > 50 else None
        out[c]['p500'] = p500
        out[c]['pend'] = ps[-1]
        out[c]['t128'] = next((10 * k for k, p in enumerate(ps) if p >= 128), None)
        out[c]['t512'] = next((10 * k for k, p in enumerate(ps) if p >= 512), None)
    return out


def load_real(mid):
    """Real metrics of a pull 2 match, or None when it has no races file (98797: raw replay deleted)."""
    if not os.path.exists(os.path.join(RACES, '%d.csv.gz' % mid)):
        return None
    with gzip.open(os.path.join(RACES, '%d.csv.gz' % mid), 'rt') as f:
        rows = [tuple(int(v) for v in d.values()) for d in csv.DictReader(f)]
    with open(os.path.join(SUMS, '%d.json' % mid), encoding='utf-8') as f:
        s = json.load(f)
    p10 = s['pop10']
    pops = [[p10[c][k] for c in range(4)] for k in range(len(p10[0]))]
    return metrics(rows, pops)


def pool(items):
    """items: [(cell name, opponent names list, colony metrics)] -> per cell pooled numbers."""
    agg = {}
    for name, opps, m in items:
        a = agg.setdefault(name, {'deaths': [0, 0, 0], 'filled': [0, 0, 0], 'own': [0, 0, 0],
                                  'span': [0, 0, 0], 'chg': [], 't128': [], 't512': [], 'cont': {}})
        for w in range(3):
            for k in ('deaths', 'filled', 'own', 'span'):
                a[k][w] += m[k][w]
        if m['p500']:
            a['chg'].append((m['pend'] - m['p500']) / m['p500'])
        a['t128'].append(m['t128'])
        a['t512'].append(m['t512'])
        for b, v in m['cont'].items():
            k = a['cont'].setdefault(opps[int(b)], [[0, 0], [0, 0], [0, 0]])
            for w in range(3):
                k[w][0] += v[w][0]
                k[w][1] += v[w][1]
    return agg


def _med(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _pct(a, b):
    return '-' if not b else '%.0f' % (100.0 * a / b)


def report(real, sim, min_cont=200):
    """Print real vs sim tables; returns the rows as a dict for checks."""
    print('\nPer cell, pooled (real / sim). own% = share of its refilled death squares it refilled itself;'
          ' d/t = its deaths per colony-tick-window (per tick, summed over its colonies / their window spans).')
    print('| cell | own% <500 | own% 500-1000 | own% >=1000 | d/t <500 | d/t 500-1000 | d/t >=1000 | '
          'chg t500->end med | t128 med | t512 med |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for n in sorted(real):
        r, s = real[n], sim.get(n)
        if s is None:
            continue
        cells = []
        for w in range(3):
            cells.append('%s / %s' % (_pct(r['own'][w], r['filled'][w]), _pct(s['own'][w], s['filled'][w])))
        for w in range(3):
            f = lambda a: '-' if not a['span'][w] else '%.2f' % (a['deaths'][w] / a['span'][w])
            cells.append('%s / %s' % (f(r), f(s)))
        f2 = lambda v, fmt: '-' if v is None else fmt % v
        cells.append('%s / %s' % (f2(_med(r['chg']), '%+.2f'), f2(_med(s['chg']), '%+.2f')))
        for k in ('t128', 't512'):
            cells.append('%s / %s' % (f2(_med(r[k]), '%d'), f2(_med(s[k]), '%d')))
        print('| %s | %s |' % (n, ' | '.join(cells)))
    print('\nContested races (both adjacent, square of a dead cell of either), won by cell vs opponent, %% real / '
          'sim (n real / n sim), pairs with >= %d real races in some window:' % min_cont)
    print('| cell | vs | <500 | 500-1000 | >=1000 |')
    print('|---|---|---|---|---|')
    for n in sorted(real):
        s = sim.get(n)
        if s is None:
            continue
        for o in sorted(real[n]['cont']):
            rv = real[n]['cont'][o]
            if max(v[0] for v in rv) < min_cont:
                continue
            sv = s['cont'].get(o, [[0, 0]] * 3)
            cells = ['%s / %s (%d / %d)' % (_pct(rv[w][1], rv[w][0]), _pct(sv[w][1], sv[w][0]), rv[w][0], sv[w][0])
                     for w in range(3)]
            print('| %s | %s | %s |' % (n, o, ' | '.join(cells)))


def main(argv=None):
    import experiments as X
    import run as R
    import validate as V
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--set', choices=('all', 'fit', 'test'), default='fit')
    ap.add_argument('--matches', help='comma list of match ids')
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--json', help='write per-match real and sim metrics here')
    ap.add_argument('--models', help='json {cell name: sim spec} overriding validate.MODELS')
    R.add_engine_args(ap)
    args = ap.parse_args(argv)
    X.lower_priority()
    table = V.load_table()
    fit, test = V.split_sets(table)
    ids = sorted(table) if args.set == 'all' else (fit if args.set == 'fit' else test)
    if args.matches:
        keep = {int(x) for x in args.matches.split(',')}
        ids = [m for m in ids if m in keep]
    table = {m: table[m] for m in ids}
    if args.models:
        V.MODELS.update({k: (v, 'model') for k, v in json.loads(args.models).items()})
    kw = R.engine_kwargs(args)
    kw['record_races'] = True
    jobs = V.make_jobs(table, V.load_starts(), kw, 1)
    t0 = time.perf_counter()
    res = X.run_jobs(jobs, args.workers, lambda r: print('match %d %.0fs' % (r['mix'], r['secs']), flush=True))
    ri, si, dump = [], [], {}
    for r in res:
        m = r['mix']
        names = r['cells']
        real = load_real(m)
        dump[m] = {'names': names, 'real': real, 'sim': r['treadmill']}
        if real is None:
            print('match %d: no real races file, left out of the treadmill tables' % m)
            continue
        for c, n in enumerate(names):
            ri.append((n, names, real[c]))
            si.append((n, names, r['treadmill'][str(c)] if str(c) in r['treadmill'] else r['treadmill'][c]))
    print('set %s, %d matches, engine %s' % (args.set, len(res), {k: v for k, v in kw.items()
                                                                     if k not in ('start_mode',)}))
    if args.models:
        print('models override:', args.models)
    report(pool(ri), pool(si))
    cmp = V.compare(table, res)
    V.print_report(cmp)
    for label, idset in (('FIT', fit), ('TEST', test)):
        sub = [r for r in res if r['mix'] in set(idset)]
        if sub:
            V.print_thresholds(V.thresholds(V.compare(table, sub)), '%s (%d games)' % (label, len(sub)))
    ins = {}
    for r in res:
        for q in r['ranking']:
            ins.setdefault(r['cells'][q['colony']], []).append(round(q['avg_insn'], 1))
    print('\nsim avg insns per call by cell (match page has the real ones):')
    for n in sorted(ins):
        print('  %-12s %s' % (n, sorted(ins[n])))
    print('\n%.0fs wall' % (time.perf_counter() - t0))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(dump, f)


if __name__ == '__main__':
    main()
