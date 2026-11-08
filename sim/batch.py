"""Run a named experiment set unattended: short markdown summary + full JSON in sim/out/.

  python batch.py --set rivals                 # sim/out/rivals-<time>.md and .json
  python batch.py --set validate               # re-play the 36 pull-2 ladder matches (validate.py)
  python batch.py --set rivals --seeds 1-16 --stun-memory drop --feed-bonus 1

Prints only the summary path when done.  At most 4 worker processes (default 4), all at below-normal
priority.  Engine options as run.py (random starts by default; the validate set uses the real starts).
"""

import argparse
import contextlib
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import experiments as X  # noqa: E402
import run as R  # noqa: E402
import validate as V  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')

VEX_CELLS = ('scourge', 'woe', 'covetous', 'conceit', 'contagion', 'endemic')
COMPLACENCY_T = tuple('complacency[free_until=%d]' % t for t in (200, 300, 500, 3000)) + (
    'complacency[diag_hold=True]',)
GROWTH_POPS = (128, 512)

SETS = {
    'rivals': {'about': 'Sprint vs the direction-ordered rival models (+ hypothetical R-Blind3)',
               'seeds': '1-8',
               'mixes': [['sprint', 'rpump', 'ratompush', 'rblind3'],
                         ['sprint', 'rbrawler', 'ratompush', 'walker'],
                         ['sprint', 'rpump', 'ratompush', 'hunter']]},
    'hypothetical': {'about': 'hypothetical fronts (R-Blind3, R-Lock5) against the measured models',
                     'seeds': '1-8',
                     'mixes': [['rblind3', 'rpump', 'ratompush', 'sprint'],
                               ['rlock5', 'rpump', 'ratompush', 'sprint']]},
    'vex': {'about': 'round 5: VEX variants vs their parents (Woe/Scourge, Conceit/Covetous, Endemic/Contagion), '
                     'head to head and each against the two rivals-set fields',
            'seeds': '1-8',
            'mixes': [['woe', 'scourge', 'rpump', 'ratompush'],
                      ['conceit', 'covetous', 'rpump', 'ratompush'],
                      ['endemic', 'contagion', 'rpump', 'ratompush']]
                     + [[c, 'rpump', 'ratompush', 'rblind3'] for c in VEX_CELLS]
                     + [[c, 'rbrawler', 'ratompush', 'walker'] for c in VEX_CELLS]},
    # designs.md 9: Complacency = Scourge plus early free splitting (no prey hold while tick < T); drafted on Woe,
    # rebased on Scourge after calib-s (Woe's VEX form is broken on the site)
    'complacency-t': {'about': 'Complacency T sweep (no prey hold while tick < T; diag = hold only for a diagonal '
                               'enemy) head to head with Scourge and in the two rival fields, with a Scourge baseline',
                      'seeds': '1-8', 'growth': True,
                      'mixes': [[v, 'scourge', 'rpump', 'ratompush'] for v in COMPLACENCY_T]
                               + [[v, 'rpump', 'ratompush', 'rblind3'] for v in COMPLACENCY_T + ('scourge',)]
                               + [[v, 'rbrawler', 'ratompush', 'walker'] for v in COMPLACENCY_T + ('scourge',)]},
    'complacency-mirror': {'about': 'Complacency vs Scourge head to head with their places in the mix swapped (start '
                                    'luck check: seeds 1-8 and 9-16 gave opposite head-to-head winners)',
                           'seeds': '1-16', 'growth': True,
                           'mixes': [['scourge', 'complacency', 'rpump', 'ratompush']]},
    'complacency': {'about': 'Complacency (chosen T) vs Scourge, head to head and in the rival fields (new seeds)',
                    'seeds': '9-16', 'growth': True,
                    'mixes': [['complacency', 'scourge', 'rpump', 'ratompush']]
                             + [[c, 'rpump', 'ratompush', 'rblind3'] for c in ('complacency', 'scourge')]
                             + [[c, 'rbrawler', 'ratompush', 'walker'] for c in ('complacency', 'scourge')]},
    'smoke': {'about': 'tiny set for tests', 'seeds': '1-2', 'mixes': [['sprint', 'rpump'], ['idle', 'walker']]},
    'validate': {'about': 'the 36 pull-2 ladder matches re-played with their real starts (validate.py)',
                 'seeds': '1'},
}


def _f(v, nd=0):
    return '-' if v is None else ('%.' + str(nd) + 'f') % v


def mix_summary(mixes, results):
    summ = X.summarize(results)
    det = X.summarize_stats(results)
    lines = []
    for m, mix in enumerate(mixes):
        res = [r for r in results if r['mix'] == m]
        ft = sorted(det[m]['freeze_ticks'])
        lines.append('')
        lines.append('## Mix %d: %s' % (m + 1, ', '.join(mix)))
        lines.append('%d games; freeze tick median %d (min %d, max %d)'
                     % (len(res), ft[len(ft) // 2], ft[0], ft[-1]))
        lines.append('')
        lines.append('| policy | pts/gm | win%% | final pop | %s | feeds/bite |'
                     % ' | '.join('land t%d' % t for t in X.LAND_TICKS))
        lines.append('|---' * (5 + len(X.LAND_TICKS)) + '|')
        for name, a in sorted(summ[m].items(), key=lambda kv: -kv[1]['points'] / kv[1]['games']):
            n = a['games']
            mean = det[m]['policies'][name]['mean']
            lines.append('| %s | %.2f | %.0f | %.0f | %s | %s |'
                         % (name, a['points'] / n, 100.0 * a['wins'] / n, a['pop'] / n,
                            ' | '.join(_f(mean[('pop', t)]) for t in X.LAND_TICKS),
                            _f(mean['feeds_per_bite'], 1)))
    return lines


def first_tick(hist, pop):
    """First tick at which a population history reaches pop (None if never)."""
    for t, p in enumerate(hist):
        if p >= pop:
            return t
    return None


def growth_summary(mixes, results):
    """Per mix and policy: mean pop at t50/t100/t200 and the median (min-max) first tick reaching GROWTH_POPS
    (pull 3 compares these with the real ladder: Scourge 128 at t36-44, 512 at t81-175; Atoms t28-33 / t56-82)."""
    lines = ['', '## Early growth (mean pop; median first tick to pop N, min-max over games; - = never)']
    for m, mix in enumerate(mixes):
        res = [r for r in results if r['mix'] == m and 'pop_history' in r]
        lines += ['', 'Mix %d: %s' % (m + 1, ', '.join(mix)), '',
                  '| policy | pop t50 | pop t100 | pop t200 | %s |' % ' | '.join('t to %d' % p for p in GROWTH_POPS),
                  '|---' * (4 + len(GROWTH_POPS)) + '|']
        for name in mix:
            pops = {t: [] for t in (50, 100, 200)}
            firsts = {p: [] for p in GROWTH_POPS}
            for r in res:
                for c, n in enumerate(r['names']):
                    if n != name:
                        continue
                    h = r['pop_history'][c]
                    for t in pops:
                        pops[t].append(h[min(t, len(h) - 1)])
                    for p in GROWTH_POPS:
                        firsts[p].append(first_tick(h, p))
            cells = []
            for p in GROWTH_POPS:
                v = sorted(x for x in firsts[p] if x is not None)
                miss = len(firsts[p]) - len(v)
                cells.append('-' if not v else '%d (%d-%d)%s' % (v[len(v) // 2], v[0], v[-1],
                                                                 ' +%d never' % miss if miss else ''))
            lines.append('| %s | %s | %s |' % (name, ' | '.join(_f(sum(v) / len(v)) if v else '-'
                                                                for v in pops.values()), ' | '.join(cells)))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--set', required=True, choices=sorted(SETS))
    ap.add_argument('--seeds', help='seed list for mix sets (e.g. 1-8), or seeds per match for validate')
    ap.add_argument('--matches', help='validate set: comma list of match ids (default all 36)')
    ap.add_argument('--workers', type=int, default=X.DEFAULT_WORKERS,
                    help='worker processes (default and maximum %d)' % X.MAX_WORKERS)
    ap.add_argument('--out', default=OUT_DIR, help='output folder (default sim/out)')
    R.add_engine_args(ap)
    args = ap.parse_args(argv)
    X.lower_priority()
    st = SETS[args.set]
    kw = R.engine_kwargs(args)
    workers = X.worker_count(args.workers)
    seeds = args.seeds or st['seeds']
    t0 = time.perf_counter()
    if args.set == 'validate':
        table = V.load_table()
        if args.matches:
            keep = {int(x) for x in args.matches.split(',')}
            table = {m: d for m, d in table.items() if m in keep}
        jobs = V.make_jobs(table, V.load_starts(), kw, int(seeds))
        results = X.run_jobs(jobs, workers)
        cmp = V.compare(table, results)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            V.print_report(cmp)
        body = ['', '```'] + buf.getvalue().strip('\n').splitlines() + ['```']
        data = {'set': args.set, 'engine': kw, 'comparison': cmp, 'matches': results}
    else:
        mixes = st['mixes']
        jobs = X.make_jobs(mixes, R.parse_seeds(seeds), kw, stats=True)
        results = X.run_jobs(jobs, workers)
        body = mix_summary(mixes, results)
        if st.get('growth'):
            body += growth_summary(mixes, results)
        data = {'set': args.set, 'mixes': mixes, 'engine': kw, 'matches': results}
    wall = time.perf_counter() - t0
    if args.set == 'validate':
        kw = dict(kw, start_mode='fixed (real starts)')
        for k in ('start_min_dist', 'start_metric', 'start_sampler'):
            kw.pop(k, None)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    os.makedirs(args.out, exist_ok=True)
    base = os.path.join(args.out, '%s-%s' % (args.set, stamp))
    head = ['# Experiment set %s (%s)' % (args.set, time.strftime('%Y-%m-%d %H:%M')),
            '', st['about'] + '.',
            '%d games, seeds %s, %.0f s wall, workers %d (below-normal priority).' % (len(results), seeds,
                                                                                     wall, workers),
            'Engine: ' + ', '.join('%s=%s' % (k, v) for k, v in sorted(kw.items())),
            'Full results: `%s`' % os.path.basename(base + '.json')]
    with open(base + '.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(head + body) + '\n')
    with open(base + '.json', 'w') as f:
        json.dump(X._jsonable(data), f)
    print(base + '.md')
    return base + '.md'


if __name__ == '__main__':
    main()
