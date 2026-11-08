"""Experiment runner: lists of policy mixes over many seeds, in parallel worker processes.

Examples (from sim/):
  python experiments.py --mix sprint,rlock5,rfatgrab,walker --seeds 1-8
  python experiments.py --mix rlock5,rfatgrab,sprint,walker --mix rblind3,rfatgrab,sprint,walker \\
                        --seeds 1-16 --workers 2 --json out.json
  python experiments.py --mix sprint,rlock5,rfatgrab,walker --seeds 1-8 --detail   # replay-style stats

Slots rotate per game within a mix (game g puts policy (s + g) mod n in slot s), as in run.py.
Policies are given as spec strings (see policies.py), so new policies plug in by registering a name.
--detail turns on the engine's event counters and records per colony: splits, moves, eats of enemies,
feeds, feeds per bite (feeds / eats of enemies), deaths, mean energy at ticks 200/500/1000, mean energy
and count of front cells (an enemy in a 4-neighbour) and interior cells at ticks 200/500/1000,
population ("land") at ticks 50/100/200/300/500/1000/2000/3000/end, the freeze tick, and the
"who bites first" pair counts (for each ordered pair of colonies, same-tick pairs of successful eats in
which A's eat came before B's).  "At tick t" = state after t ticks; a match that ended earlier reports
its final state.  Engine options are the same as run.py's (random starts are the default).
At most 2 worker processes (default 2), all at below-normal priority.
"""

import argparse
import json
import multiprocessing
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine as E  # noqa: E402
import policies  # noqa: E402
import run as R  # noqa: E402

POP_TICKS = (50, 100, 200, 300, 500, 1000, 2000, 3000)    # "land" = population (one cell per square)
LAND_TICKS = (300, 500, 1000, 2000, 3000)
ENERGY_TICKS = (200, 500, 1000)
STAT_KEYS = ('splits', 'moves', 'eats_enemy', 'eats_friend', 'feeds', 'deaths', 'stuns')
FRONT_TICKS = (200, 500, 1000)
FREEZE_TOL = 0.05

# CPU limit (user, 2026-11-07): never more than 2 worker processes, all at below-normal priority.
DEFAULT_WORKERS = 2
MAX_WORKERS = 2
_BELOW_NORMAL_PRIORITY_CLASS = 0x4000


def worker_count(workers=None):
    """Worker processes to use: DEFAULT_WORKERS when None, clamped to [1, MAX_WORKERS]."""
    if workers is None:
        workers = DEFAULT_WORKERS
    return max(1, min(MAX_WORKERS, int(workers)))


def lower_priority():
    """Put this process at below-normal priority (Windows, via ctypes); a no-op elsewhere or on error."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), _BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def freeze_tick(history, tol=FREEZE_TOL):
    """Earliest t such that, for every colony, every population from t on lies within [p(t) * (1 - tol),
    p(t) * (1 + tol)].  Same definition as the replay analyzer (tools/pull2/analyze.js).
    history = one list per colony, index = tick (state after that many ticks)."""
    T = len(history[0])
    n = len(history)
    mx = [0] * n
    mn = [float('inf')] * n
    best = T
    for t in range(T - 1, -1, -1):
        ok = True
        for c in range(n):
            p = history[c][t]
            if p > mx[c]:
                mx[c] = p
            if p < mn[c]:
                mn[c] = p
            if not (mx[c] <= p * (1 + tol) and mn[c] >= p * (1 - tol)):
                ok = False
        if not ok:
            break
        best = t
    return best


def front_energy(eng):
    """Per colony (mean energy, count) of front cells: living cells with an enemy in a 4-neighbour."""
    return front_interior(eng)[0]


def front_interior(eng):
    """(front, interior): per colony (mean energy, count) of front cells (an enemy in a 4-neighbour, as in
    the replay analysis) and of all other living cells."""
    grid, col, en, alive = eng.grid, eng.c_col, eng.c_en, eng.c_alive
    dirs = eng.dirs
    sums = [0] * E.MAX_COLONIES
    cnt = [0] * E.MAX_COLONIES
    isum = [0] * E.MAX_COLONIES
    icnt = [0] * E.MAX_COLONIES
    for i in eng.live:
        if not alive[i]:
            continue
        p = eng.c_pos[i]
        c = col[i]
        for o in dirs:
            g = grid[p + o]
            if g >= 0 and alive[g] and col[g] != c:
                sums[c] += en[i]
                cnt[c] += 1
                break
        else:
            isum[c] += en[i]
            icnt[c] += 1
    rng = range(E.MAX_COLONIES)
    return ([((sums[c] / cnt[c]) if cnt[c] else None, cnt[c]) for c in rng],
            [((isum[c] / icnt[c]) if icnt[c] else None, icnt[c]) for c in rng])


def make_jobs(mixes, seeds, engine_kw, stats=False, rotate=True):
    """One job (a plain, picklable dict) per (mix, seed)."""
    jobs = []
    for m, mix in enumerate(mixes):
        mix = list(mix)
        for g, seed in enumerate(seeds):
            k = g % len(mix) if rotate else 0
            jobs.append({'mix': m, 'game': g, 'seed': seed, 'names': mix[k:] + mix[:k],
                         'engine': dict(engine_kw), 'stats': bool(stats)})
    return jobs


def play_job(job):
    """Play one match; returns a picklable result dict."""
    names = job['names']
    stats = job['stats']
    eng = E.Engine([policies.get(n) for n in names], seed=job['seed'], record_events=stats, **job['engine'])
    t0 = time.perf_counter()
    marks = {}
    fronts = {}
    ncol = len(names)
    hist = [[eng.pop[c]] for c in range(ncol)]
    if stats:
        want = set(POP_TICKS) | set(ENERGY_TICKS)
        more = True
        while more:
            more = eng.step()
            for c in range(ncol):
                hist[c].append(eng.pop[c])
            if eng.tick in want:
                marks[eng.tick] = (list(eng.pop), list(eng.energy))
            if eng.tick in FRONT_TICKS:
                fronts[eng.tick] = front_interior(eng)
    else:
        eng.run()
    secs = time.perf_counter() - t0
    ranking = eng.ranking()
    for r in ranking:
        r['name'] = names[r['colony']]
    out = {'mix': job['mix'], 'game': job['game'], 'seed': job['seed'], 'names': list(names),
           'ticks': eng.tick, 'secs': secs, 'ranking': ranking,
           'starts': {c: list(xy) for c, xy in eng.start_positions.items()}}
    if stats:
        final = (list(eng.pop), list(eng.energy))
        final_front = front_interior(eng)
        st = []
        for c in range(len(names)):
            pop_at = {t: marks.get(t, final)[0][c] for t in POP_TICKS}
            pop_at['end'] = eng.pop[c]
            energy_at = {}
            for t in ENERGY_TICKS:
                p, e = marks.get(t, final)
                energy_at[t] = (e[c] / p[c]) if p[c] else None
            s = {'name': names[c], 'splits': eng.births[c], 'moves': eng.moves[c],
                 'eats_enemy': eng.eats_enemy[c], 'eats_friend': eng.eats_friend[c], 'feeds': eng.feeds[c],
                 'deaths': eng.deaths[c], 'stuns': eng.stuns[c], 'pop_at': pop_at, 'energy_at': energy_at,
                 'front_at': {t: fronts.get(t, final_front)[0][c] for t in FRONT_TICKS},
                 'interior_at': {t: fronts.get(t, final_front)[1][c] for t in FRONT_TICKS},
                 'feeds_per_bite': (eng.feeds[c] / eng.eats_enemy[c]) if eng.eats_enemy[c] else None}
            st.append(s)
        out['stats'] = st
        out['bite_first'] = [row[:] for row in eng.bite_first]
        out['pop_history'] = hist
        out['freeze_tick'] = freeze_tick(hist)
        if eng.deltas is not None:
            out['deltas'] = {k: dict(v) for k, v in eng.deltas.items()}
    return out


def run_jobs(jobs, workers=None, progress=None):
    """Results in job order.  workers: None -> DEFAULT_WORKERS, capped at MAX_WORKERS; 1 runs in this
    process.  Worker processes start at below-normal priority."""
    workers = worker_count(workers)
    if workers <= 1 or len(jobs) <= 1:
        out = []
        for j in jobs:
            out.append(play_job(j))
            if progress:
                progress(out[-1])
        return out
    ctx = multiprocessing.get_context('spawn')
    out = []
    with ctx.Pool(min(workers, len(jobs)), initializer=lower_priority) as pool:
        for r in pool.imap(play_job, jobs, chunksize=1):
            out.append(r)
            if progress:
                progress(r)
    return out


def summarize(results):
    """{mix: {policy: {games, points, wins, pop, place}}} (sums; see print_summary for means)."""
    summ = {}
    for r in results:
        mix = summ.setdefault(r['mix'], {})
        for x in r['ranking']:
            a = mix.setdefault(x['name'], {'games': 0, 'points': 0, 'wins': 0, 'pop': 0, 'place': 0})
            a['games'] += 1
            a['points'] += x['points']
            a['wins'] += x['place'] == 1
            a['pop'] += x['pop']
            a['place'] += x['place']
    return summ


def summarize_stats(results):
    """Per mix: mean replay-style stats per policy and bite-first pair sums by policy name."""
    out = {}
    for r in results:
        if 'stats' not in r:
            continue
        mix = out.setdefault(r['mix'], {'policies': {}, 'bite_first': {}, 'freeze_ticks': []})
        mix['freeze_ticks'].append(r['freeze_tick'])
        for s in r['stats']:
            a = mix['policies'].setdefault(s['name'], {'n': 0, 'sums': {}, 'en_n': {}})
            a['n'] += 1
            sums = a['sums']
            for k in STAT_KEYS:
                sums[k] = sums.get(k, 0) + s[k]
            for t, v in s['pop_at'].items():
                sums[('pop', t)] = sums.get(('pop', t), 0) + v
            for t, v in s['energy_at'].items():
                if v is not None:
                    sums[('en', t)] = sums.get(('en', t), 0) + v
                    a['en_n'][t] = a['en_n'].get(t, 0) + 1
            for key, kn in (('front_at', 'front'), ('interior_at', 'interior')):
                for t, (v, cnt) in s.get(key, {}).items():
                    sums[(kn + '_n', t)] = sums.get((kn + '_n', t), 0) + cnt
                    if v is not None:
                        sums[(kn, t)] = sums.get((kn, t), 0) + v
                        a['en_n'][(kn, t)] = a['en_n'].get((kn, t), 0) + 1
        names = r['names']
        m = r['bite_first']
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                if a != b:
                    mix['bite_first'][(a, b)] = mix['bite_first'].get((a, b), 0) + m[i][j]
    for mix in out.values():
        for a in mix['policies'].values():
            n = a['n']
            means = {k: v / n for k, v in a['sums'].items()
                     if not (isinstance(k, tuple) and k[0] in ('en', 'front', 'interior'))}
            for t in ENERGY_TICKS:
                c = a['en_n'].get(t, 0)
                means[('en', t)] = a['sums'][('en', t)] / c if c else None
            for kn in ('front', 'interior'):
                for t in FRONT_TICKS:
                    c = a['en_n'].get((kn, t), 0)
                    means[(kn, t)] = a['sums'][(kn, t)] / c if c else None
            # pooled, as in the replay report: total feeds / total eats of enemies
            means['feeds_per_bite'] = (a['sums']['feeds'] / a['sums']['eats_enemy']
                                       if a['sums']['eats_enemy'] else None)
            a['mean'] = means
    return out


# ---- printing --------------------------------------------------------------------------------------
def _fmt(v, nd=0):
    if v is None:
        return 'dead'
    return ('%.' + str(nd) + 'f') % v


def stat_rows(names, get):
    """Rows of the replay-style table: (label, [value per column]).  get(name_or_idx, key) -> value."""
    rows = [('splits', 'splits', 0), ('moves', 'moves', 0), ('eats of enemies', 'eats_enemy', 0),
            ('eats of friends', 'eats_friend', 0), ('feeds', 'feeds', 0), ('deaths', 'deaths', 0)]
    out = [(label, [_fmt(get(c, k), nd) for c in names]) for label, k, nd in rows]

    out.append(('feeds per bite', [_fmt(get(c, 'feeds_per_bite'), 1) if get(c, 'feeds_per_bite') is not None
                                   else '-' for c in names]))
    for t in ENERGY_TICKS:
        out.append(('mean energy t%d' % t, [_fmt(get(c, ('en', t)), 1) for c in names]))
    for kn in ('front', 'interior'):
        for t in FRONT_TICKS:
            out.append(('%s energy t%d (n)' % (kn, t),
                        ['%s (%s)' % (_fmt(get(c, (kn, t)), 1) if get(c, (kn, t)) is not None else '-',
                                      _fmt(get(c, (kn + '_n', t)), 0)) for c in names]))
    for t in POP_TICKS[:3]:
        out.append(('pop t%s' % t, [_fmt(get(c, ('pop', t)), 0) for c in names]))
    for t in LAND_TICKS:
        out.append(('land t%s' % t, [_fmt(get(c, ('pop', t)), 0) for c in names]))
    out.append(('final pop', [_fmt(get(c, ('pop', 'end')), 0) for c in names]))
    return out


def print_table(header, rows):
    w0 = max(len(r[0]) for r in rows + [('', [])])
    ws = [max(len(h), max(len(r[1][i]) for r in rows)) for i, h in enumerate(header)]
    print('  %-*s  %s' % (w0, '', '  '.join('%*s' % (w, h) for w, h in zip(ws, header))))
    for label, vals in rows:
        print('  %-*s  %s' % (w0, label, '  '.join('%*s' % (w, v) for w, v in zip(ws, vals))))


def print_match_detail(r):
    names = r['names']
    st = r['stats']

    def get(c, k):
        s = st[c]
        if isinstance(k, tuple):
            if k[0] == 'pop':
                return s['pop_at'][k[1]]
            if k[0] in ('front', 'interior'):
                return s[k[0] + '_at'][k[1]][0]
            if k[0] in ('front_n', 'interior_n'):
                return s[k[0][:-2] + '_at'][k[1]][1]
            return s['energy_at'][k[1]]
        return s[k]
    place = {x['colony']: x['place'] for x in r['ranking']}
    print('match mix %d seed %d  ticks %d  freeze tick %d  %.1fs  starts %s'
          % (r['mix'] + 1, r['seed'], r['ticks'], r['freeze_tick'], r['secs'],
             ' '.join('%s(%d,%d)' % (names[c], x, y) for c, (x, y) in sorted(r['starts'].items()))))
    header = ['%d.%s' % (place[c], n) for c, n in enumerate(names)]
    print_table(header, stat_rows(range(len(names)), get))
    print_bite_first([(names[a], names[b], r['bite_first'][a][b], r['bite_first'][b][a])
                      for a in range(len(names)) for b in range(a + 1, len(names))])


def print_bite_first(pairs):
    print('  bites first (same-tick eat pairs, A before B / B before A):')
    for a, b, ab, ba in pairs:
        tot = ab + ba
        share = ' (%.0f%% %s)' % (100.0 * ab / tot, a) if tot else ''
        print('    %-12s vs %-12s %9d / %-9d%s' % (a, b, ab, ba, share))


def print_summary(mixes, results):
    summ = summarize(results)
    detail = summarize_stats(results)
    for m, mix in enumerate(mixes):
        res = [r for r in results if r['mix'] == m]
        print('\nmix %d: %s   (%d games, mean %.1fs/match, %.0f ticks)'
              % (m + 1, ','.join(mix), len(res), sum(r['secs'] for r in res) / max(1, len(res)),
                 sum(r['ticks'] for r in res) / max(1, len(res))))
        print('  %-28s %5s %7s %6s %9s %9s' % ('policy', 'games', 'pts/gm', 'win%', 'avg place', 'avg pop'))
        for name, a in sorted(summ.get(m, {}).items(), key=lambda kv: (-kv[1]['points'] / kv[1]['games'], kv[0])):
            n = a['games']
            print('  %-28s %5d %7.2f %6.1f %9.2f %9.1f' % (name, n, a['points'] / n, 100.0 * a['wins'] / n,
                                                       a['place'] / n, a['pop'] / n))
        if m in detail:
            d = detail[m]
            names = list(dict.fromkeys(mix))
            ft = sorted(d['freeze_ticks'])
            print('  freeze tick (all colonies within 5%% of their later pop): median %d, min %d, max %d'
                  % (ft[len(ft) // 2], ft[0], ft[-1]))
            print('  mean over matches (feeds per bite pooled):')
            print_table(names, stat_rows(names, lambda c, k: d['policies'][c]['mean'][k]))
            bf = d['bite_first']
            print_bite_first([(a, b, bf.get((a, b), 0), bf.get((b, a), 0))
                              for i, a in enumerate(names) for b in names[i + 1:]])


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mix', action='append', required=True,
                    help='comma list of 1-4 policy specs (repeat for several mixes)')
    ap.add_argument('--seeds', default='1-8', help='e.g. 1-8 or 1,4,9')
    ap.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                    help='worker processes (default %d, at most %d; below-normal priority)'
                         % (DEFAULT_WORKERS, MAX_WORKERS))
    ap.add_argument('--detail', action='store_true', help='per-match replay-style stats (event counters)')
    ap.add_argument('--quiet', action='store_true', help='with --detail: only the per-mix means')
    ap.add_argument('--no-rotate', action='store_true')
    ap.add_argument('--json', help='write all match results to this file')
    R.add_engine_args(ap)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    lower_priority()
    mixes = [policies.split_specs(m) for m in args.mix]
    for mix in mixes:
        if not 1 <= len(mix) <= 4:
            raise SystemExit('a mix has 1 to 4 policies')
        for n in mix:
            R.load_policy(n)
    seeds = R.parse_seeds(args.seeds)
    jobs = make_jobs(mixes, seeds, R.engine_kwargs(args), stats=args.detail, rotate=not args.no_rotate)
    t0 = time.perf_counter()

    def progress(r):
        print('mix %d seed %-4d %6.1fs %5d ticks  %s' % (
            r['mix'] + 1, r['seed'], r['secs'], r['ticks'],
            '  '.join('%d.%s(%d)' % (x['place'], x['name'], x['pop']) for x in r['ranking'])), flush=True)
    results = run_jobs(jobs, args.workers, progress)
    wall = time.perf_counter() - t0
    if args.detail and not args.quiet:
        for r in results:
            print()
            print_match_detail(r)
    print_summary(mixes, results)
    print('\n%d matches, %.1fs wall' % (len(results), wall))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(_jsonable({'mixes': mixes, 'seeds': seeds, 'engine': R.engine_kwargs(args),
                                 'matches': results}), f)


if __name__ == '__main__':
    main()
