"""Sanity check of the simulator against real ladder replays (data pull 2).

Re-plays the 36 analysed ladder matches with the same start squares and the nearest sim model of each
cell, then compares the replay-style statistics with data/pull2/validation-table.md and the rule
statistics of data/ladder-data-2-2026-11-08.md (section 6).  Reads the data files; writes nothing there.

  python validate.py                          # all 36 matches, 1 sim seed each, 2 workers
  python validate.py --seeds 3 --json v.json  # 3 sim seeds per match
  python validate.py --feed-bonus 1 --idle-gain 0.08   # the two unexplained effects switched on

Cell models (MODELS) are approximations.  'model' = a rival modelled on its measured profile (direction
order, split threshold, feeding style; rivals.py); 'rough' = a cell with no model, stood in for by an
open bot of similar behaviour (no feeding -> hunter, moving -> walker).  Results are shown for all
matches and for the matches with no 'rough' cell.
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import experiments as X  # noqa: E402
import run as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, 'data', 'pull2', 'validation-table.md')
REPORT = os.path.join(ROOT, 'data', 'ladder-data-2-2026-11-08.md')

# cell name -> (sim spec, quality).  Profiles from data/ladder-data-2-2026-11-08.md sections 3-4.
MODELS = {
    'Sprint': ('sprint', 'exact'),
    'Hunter': ('hunter', 'exact'), 'Medic': ('medic', 'exact'), 'Walker': ('walker', 'exact'),
    'Random': ('random', 'exact'),
    'Brawler': ('rpump[split_min=6]', 'model'),                 # U4 L6, split 6, feeds/eat 48
    'Brawler v2': ('rpump', 'model'),                           # U4 L6, split 5, pump
    'Bouncer': ('rpump[order=DRLU,split_min=6]', 'model'),      # D4 R6, split 6, pump
    'Aegis': ('rpump', 'model'),                                # U fast only, pump-ish (interior 19)
    'Noob+': ('rpump[order=DLRU]', 'model'),                    # D fast only
    'Noob++': ('rpump[order=DLRU]', 'model'),
    'AtomPush': ('ratompush', 'model'),                         # R4 L6, fat economy
    'AtomCrasher': ('ratompush', 'model'),                      # R4 L6, fat, feeds less
    'rooby': ('ratompush[order=URDL,split_min=6,assist_min=99,donor_min=99]', 'model'),  # U4 R6, no feeding
    'Noob': ('hunter', 'rough'), 'squirtle': ('hunter', 'rough'), 'gemAlert_v3': ('hunter', 'rough'),
    'gemAlert_v4': ('hunter', 'rough'), 'Bulwark': ('hunter', 'rough'),
    'zergling': ('walker', 'rough'), 'choochoo': ('walker', 'rough'),
}
COLS = ('t50', 't100', 't200', 't500', 't1000', 'end', 'E200', 'E1000', 'fpe')


def _num(text):
    text = text.strip()
    if text in ('None', '-', ''):
        return None
    return float(text)


def load_table(path=TABLE):
    """{match id: {'freeze': int, 'rows': [{'cell', 't50', ..., 'fpe'}] in colony order}}."""
    out = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = [p.strip() for p in line.strip().strip('|').split('|')]
            if len(parts) != 12 or not parts[0].isdigit():
                continue
            m = int(parts[0])
            row = {'cell': parts[1]}
            for k, v in zip(COLS, parts[2:11]):
                row[k] = _num(v)
            d = out.setdefault(m, {'freeze': int(parts[11]), 'rows': []})
            d['rows'].append(row)
    return out


def load_starts(path=REPORT):
    """{match id: [(cell, (x, y)), ...]} from section 5 of the pull 2 report (colony order)."""
    with open(path, encoding='utf-8') as f:
        txt = f.read()
    sec = txt.split('## 5.')[1].split('```')[1]
    out = {}
    for line in sec.strip().splitlines():
        m, rest = line.split(':', 1)
        out[int(m)] = [(n.strip(), (int(x), int(y))) for n, x, y in
                       re.findall(r'([^;]+?) \((\d+),(\d+)\)', rest)]
    return out


def make_jobs(table, starts, engine_kw, seeds=1):
    jobs = []
    for m in sorted(table):
        cells = [r['cell'] for r in table[m]['rows']]
        if m not in starts or [n for n, _ in starts[m]] != cells:
            raise ValueError('start list of %d does not match the table' % m)
        specs = [MODELS[n][0] for n in cells]
        kw = dict(engine_kw, start_mode='fixed', start_positions=[xy for _, xy in starts[m]],
                  record_deltas=True)
        for k in range(seeds):
            jobs.append({'mix': m, 'game': k, 'seed': m * 100 + k, 'names': specs, 'engine': kw,
                         'stats': True, 'cells': cells})
    return jobs


def sim_row(r, c):
    s = r['stats'][c]
    pa = s['pop_at']
    return {'t50': pa[50], 't100': pa[100], 't200': pa[200], 't500': pa[500], 't1000': pa[1000],
            'end': pa['end'], 'E200': s['energy_at'][200], 'E1000': s['energy_at'][1000],
            'fpe': s['feeds_per_bite']}


def winner(rows):
    """Index of the colony with the largest final population (the real table has no energy column)."""
    return max(range(len(rows)), key=lambda c: rows[c]['end'])


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def compare(table, results):
    """Comparison dict: per cell medians, freeze ticks, winners, deltas.  Pure function of its inputs."""
    by_match = {}
    for r in results:
        by_match.setdefault(r['mix'], []).append(r)
    out = {'matches': [], 'cells': {}, 'deltas': {'idle': {}, 'fed': {}}}
    for m in sorted(by_match):
        real = table[m]['rows']
        cells = [x['cell'] for x in real]
        clean = all(MODELS[n][1] != 'rough' for n in cells)
        for r in by_match[m]:
            sim = [sim_row(r, c) for c in range(len(cells))]
            out['matches'].append({
                'match': m, 'seed': r['seed'], 'clean': clean, 'cells': cells,
                'real_freeze': table[m]['freeze'], 'sim_freeze': r['freeze_tick'],
                'real_winner': cells[winner(real)], 'sim_winner': cells[winner(sim)],
                'real_frozen_t500': table[m]['freeze'] <= 500, 'sim_frozen_t500': r['freeze_tick'] <= 500,
                'real_end': [x['end'] for x in real], 'sim_end': [x['end'] for x in sim]})
            for c, n in enumerate(cells):
                a = out['cells'].setdefault(n, {'real': {k: [] for k in COLS}, 'sim': {k: [] for k in COLS},
                                                'quality': MODELS[n][1], 'spec': MODELS[n][0]})
                for k in COLS:
                    a['real'][k].append(real[c][k])
                    a['sim'][k].append(sim[c][k])
            for k in ('idle', 'fed'):
                for d, cnt in r.get('deltas', {}).get(k, {}).items():
                    out['deltas'][k][int(d)] = out['deltas'][k].get(int(d), 0) + cnt
    return out


def _f(v, nd=0):
    return '-' if v is None else ('%.' + str(nd) + 'f') % v


def print_report(cmp):
    ms = cmp['matches']
    for label, sel in (('all matches', ms), ('matches with no rough stand-in', [x for x in ms if x['clean']])):
        if not sel:
            continue
        rf = [x['real_freeze'] for x in sel]
        sf = [x['sim_freeze'] for x in sel]
        print('\n== %s (%d sim games, %d distinct matches) ==' % (label, len(sel), len({x['match'] for x in sel})))
        print('freeze tick       real median %s (min %d, max %d)   sim median %s (min %d, max %d)'
              % (_f(median(rf)), min(rf), max(rf), _f(median(sf)), min(sf), max(sf)))
        print('frozen by t500    real %d / %d   sim %d / %d'
              % (sum(x['real_frozen_t500'] for x in sel), len(sel), sum(x['sim_frozen_t500'] for x in sel),
                 len(sel)))
        print('same winner       %d / %d' % (sum(x['real_winner'] == x['sim_winner'] for x in sel), len(sel)))
        sp = [x for x in sel if 'Sprint' in x['cells']]
        if sp:
            print('Sprint wins       real %d / %d   sim %d / %d'
                  % (sum(x['real_winner'] == 'Sprint' for x in sp), len(sp),
                     sum(x['sim_winner'] == 'Sprint' for x in sp), len(sp)))
    print('\n== per cell: median real / sim over its colonies ==')
    hdr = ('cell', 'spec', 'n') + COLS
    print('%-12s %-12s %3s ' % hdr[:3] + ' '.join('%13s' % h for h in COLS))
    for n, a in sorted(cmp['cells'].items(), key=lambda kv: (kv[1]['quality'], kv[0])):
        vals = []
        for k in COLS:
            nd = 1 if k in ('E200', 'E1000', 'fpe') else 0
            vals.append('%6s/%-6s' % (_f(median(a['real'][k]), nd), _f(median(a['sim'][k]), nd)))
        print('%-12s %-12s %3d ' % (n, a['quality'], len(a['real']['t50'])) + ' '.join('%13s' % v for v in vals))
    print('\n== rule statistics (pull 2 section 6 vs sim) ==')
    idle = cmp['deltas']['idle']
    tot = sum(idle.values())
    if tot:
        print('no-event cell-ticks ending +1: real 8.0%% (17.25M of 216M)   sim %.1f%% (%d of %d; sim counts '
              'REST as no event)' % (100.0 * idle.get(1, 0) / tot, idle.get(1, 0), tot))
    fed = cmp['deltas']['fed']
    tot = sum(fed.values())
    if tot:
        real = {3: 6.38, 2: 0.228, 0: 2.1}
        rt = sum(real.values())
        print('fed-once receivers: real +3 %.0f%%, +2 %.0f%%, +0 %.0f%% (of the three)   sim +3 %.0f%%, +2 %.0f%%, '
              '+0 %.0f%%, other %.0f%%'
              % tuple([100 * real[k] / rt for k in (3, 2, 0)] +
                      [100.0 * fed.get(k, 0) / tot for k in (3, 2, 0)] +
                      [100.0 * sum(v for k, v in fed.items() if k not in (3, 2, 0)) / tot]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seeds', type=int, default=1, help='sim seeds per real match')
    ap.add_argument('--workers', type=int, default=X.DEFAULT_WORKERS,
                    help='worker processes (default and maximum %d)' % X.MAX_WORKERS)
    ap.add_argument('--matches', help='comma list of match ids (default: all in the table)')
    ap.add_argument('--json', help='write the comparison to this file')
    R.add_engine_args(ap)
    args = ap.parse_args(argv)
    X.lower_priority()
    table = load_table()
    if args.matches:
        keep = {int(x) for x in args.matches.split(',')}
        table = {m: d for m, d in table.items() if m in keep}
    kw = R.engine_kwargs(args)
    jobs = make_jobs(table, load_starts(), kw, args.seeds)
    t0 = time.perf_counter()
    res = X.run_jobs(jobs, args.workers, lambda r: print('match %d seed %d %.0fs' % (r['mix'], r['seed'], r['secs']),
                                                         flush=True))
    cmp = compare(table, res)
    print('engine: %s' % {k: v for k, v in kw.items() if k not in ('start_mode',)})
    print_report(cmp)
    print('\n%d games, %.0fs wall' % (len(res), time.perf_counter() - t0))
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(X._jsonable(cmp), f)


if __name__ == '__main__':
    main()
