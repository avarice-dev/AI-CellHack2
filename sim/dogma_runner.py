"""Dogma local gauntlet (spec shared/cellhack2/COMPREHENSIVE_REPORT.md section 7.3): our own reference cells and the
calibrated rival models only; no site access.  Run from sim/:

  python dogma_runner.py --stage solo            # 11 solo starts, Dogma vs Bane v2.2, cells at t20..t100 (gate: 0/11 regressions)
  python dogma_runner.py --stage m16             # 16x16, 500 ticks, 4 players, seeds x 4 seat rotations
  python dogma_runner.py --stage m64             # 64x64, 3000 ticks, 4 players: mixes A, B (+ control Bc), C (+ control Cc)
  python dogma_runner.py --stage duel            # 1v1 backed front duels, 50 energy everywhere, 3000 ticks
  python dogma_runner.py --stage abl             # ablations K_CAP 12/25, k(1..2)=0, QUIET_FEED_CAP 28/38 on mixes A and B
  python dogma_runner.py --stage all             # solo, m16, m64, duel, abl in this order
  --seeds 1-4  --workers 6 (default and maximum, normal priority)  --report-only  --out DIR
Each finished game appends one JSON line to <out>/<stage>.jsonl (a restart skips games already there); every stage
writes <out>/<stage>-report.md.  Nothing is truncated: a game runs to its tick limit or until one colony is left.

Mixes (the first name is the focus colony: Dogma or its control; seat = rotation r puts it in slot r):
  A  dogma, m353 (make_misfortune2_split10), bane22 (Bane v2.2), dep_c4d (Depravity as of commit c4d7350, T_FEED 200)
  B  dogma, rsiectf, rvarsi, ratompush            (Bc: m353 in place of dogma)
  C  dogma, rsiectf, m353, bane22 on fixed equal-start squares   (Cc: dep_c4d in place of dogma)
rivals.py has no AtomVirus model: ratompush (AtomPush / HammerSpb, the fat-body refill rival) is the nearest proxy.
Telemetry per focus colony: faults, 48 <-> 50 lock cell-ticks (a cell's last four energies alternate 48 / 50 AND it armed at energy 50 within
those ticks = the stalled 17/15-insn rescan; plain alternation and arm@50 calls are reported too), t < 100
feed share of cell-ticks, per window (<100, 100-300, 300-1000, 1000+) calls / feeds / eats / stuns / friendly eats / cells.
"""

import argparse
import collections
import importlib.util
import json
import multiprocessing
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import cells_ref as C  # noqa: E402
import engine as E  # noqa: E402

OUT_DIR = os.path.join(HERE, 'out', 'dogma')
WINDOWS = ((0, 100, '<100'), (100, 300, '100-300'), (300, 1000, '300-1000'), (1000, 10 ** 9, '1000+'))
MAX_WORKERS = 6
DUEL_SIDE = 8                       # duel board 16 x 16: colony in slot 0 on x < 8, slot 1 on x >= 8, 50 energy everywhere
FIXED_STARTS = ((16, 16), (47, 16), (16, 47), (47, 47))
DEP_COMMIT = 'c4d7350'
ABLATIONS = {'k_cap12': dict(k_cap=12), 'k_cap25': dict(k_cap=25), 'k12_0': dict(k12=0),
             'quiet28': dict(quiet_cap=28), 'quiet38': dict(quiet_cap=38)}
MIXES = {'A': ('dogma', 'm353', 'bane22', 'dep_c4d'),
         'B': ('dogma', 'rsiectf', 'rvarsi', 'ratompush'),
         'Bc': ('m353', 'rsiectf', 'rvarsi', 'ratompush'),
         'C': ('dogma', 'rsiectf', 'm353', 'bane22'),
         'Cc': ('dep_c4d', 'rsiectf', 'm353', 'bane22')}


def window_of(t):
    for lo, hi, name in WINDOWS:
        if lo <= t < hi:
            return name


def parse_seeds(s):
    out = []
    for part in s.split(','):
        if '-' in part:
            a, b = part.split('-')
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def _dep_module():
    """Depravity's reference exactly as of DEP_COMMIT (live cell 363 = c4d7350), loaded from git next to the log."""
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, 'cells_ref_%s.py' % DEP_COMMIT)
    if not os.path.exists(path):
        src = subprocess.run(['git', 'show', '%s:sim/cells_ref.py' % DEP_COMMIT], cwd=ROOT, capture_output=True, check=True).stdout
        with open(path, 'wb') as f:
            f.write(src)
    spec = importlib.util.spec_from_file_location('cells_ref_c4d', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _ViewProxy(object):
    """The c4d7350 reference copies the view and assigns v2.cells = ...; the engine's View has read-only properties."""

    def __init__(self, v):
        self._v = v

    def __getattr__(self, n):
        if n.startswith('__') or n == '_v':
            raise AttributeError(n)
        return getattr(self._v, n)


def _proxied(pol):
    def depravity_c4d(view, mem):
        return pol(_ViewProxy(view), mem)
    return depravity_c4d


def policy(name):
    """name -> policy.  'dogma' or 'dogma:k_cap=12' (ablation key from ABLATIONS)."""
    if name.startswith('dogma'):
        kw = ABLATIONS[name.split(':')[1]] if ':' in name else {}
        return C.make_dogma(**kw)
    if name == 'm353':
        return C.make_misfortune2_split10()
    if name == 'bane22':
        return C.make_bane2()
    if name == 'dep_c4d':
        return _proxied(_dep_module().make_depravity())
    import policies
    return policies.get(name)


class Meter(object):
    """Counters for the focus colony: wraps its policy, hooks the engine, scans energies after every tick."""

    def __init__(self, seat, pol):
        self.seat = seat
        self.pol = pol
        self.eng = None
        self.c = collections.Counter()
        self.hist = {}
        self.locked = set()
        self.snap = {}
        self.insn = collections.Counter()
        self.arm50 = {}

        def wrapped(view, mem):
            r = self.pol(view, mem)
            w = window_of(view.tick)
            self.c[(w, 'calls')] += 1
            k = r[0] & 0xF0
            if k == E.ACT_FEED:
                self.c[(w, 'feeds')] += 1
            elif k == E.ACT_EAT:
                self.c[(w, 'eat_calls')] += 1
            self.insn[r[1]] += 1
            if view.energy == 50 and r[1] == 15 and k == E.ACT_EAT:
                self.c['arm50_calls'] += 1
                self.arm50[(view.x, view.y)] = view.tick
            return r
        self.policy = wrapped

    def attach(self, eng):
        self.eng = eng

    def after_tick(self):
        eng, seat = self.eng, self.seat
        t = eng.tick
        col, en, alive = eng.c_col, eng.c_en, eng.c_alive
        hist, locked = self.hist, self.locked
        for i in eng.live:
            if col[i] != seat or not alive[i]:
                continue
            e = en[i]
            h = hist.get(i)
            if h is None:
                hist[i] = (e,)
                continue
            if e in (48, 50) or (h and h[-1] in (48, 50)):
                h = (h + (e,))[-4:]
                hist[i] = h
                if h == (48, 50, 48, 50) or h == (50, 48, 50, 48):
                    self.c['alt_cell_ticks'] += 1
                    p = eng.c_pos[i]
                    if t - self.arm50.get((p % eng.PW - 2, p // eng.PW - 2), -99) <= 4:     # armed at 50 inside the window: the stall
                        self.c['lock_cell_ticks'] += 1
                        if i not in locked:
                            locked.add(i)
                            self.c['lock_cells'] += 1
            else:
                hist[i] = (e,)
        for edge in (100, 300, 1000):
            if t == edge:
                self.snap[edge] = (eng.eats_enemy[seat], eng.eats_friend[seat], eng.stuns[seat], eng.feeds[seat],
                                   eng.pop[seat], eng.births[seat], eng.deaths[seat])

    def result(self):
        eng, seat = self.eng, self.seat
        end = (eng.eats_enemy[seat], eng.eats_friend[seat], eng.stuns[seat], eng.feeds[seat], eng.pop[seat],
               eng.births[seat], eng.deaths[seat])
        snaps = [(0, (0,) * 7)] + [(k, self.snap[k]) for k in (100, 300, 1000) if k in self.snap] + [(10 ** 9, end)]
        buckets = {}
        names = ('eats_enemy', 'eats_friend', 'stuns', 'feeds', 'cells_end', 'births', 'deaths')
        for (a, sa), (b, sb) in zip(snaps, snaps[1:]):
            w = window_of(a)
            d = {n: (sb[j] - sa[j]) if names[j] != 'cells_end' else sb[j] for j, n in enumerate(names)}
            d['calls'] = self.c[(w, 'calls')]
            d['feed_calls'] = self.c[(w, 'feeds')]
            buckets[w] = d
        c100 = self.c[('<100', 'calls')]
        return {'alt_cell_ticks': self.c['alt_cell_ticks'], 'arm50_calls': self.c['arm50_calls'],
                'lock_cell_ticks': self.c['lock_cell_ticks'], 'lock_cells': self.c['lock_cells'],
                'feed_lt100_pct': round(100.0 * self.c[('<100', 'feeds')] / c100, 4) if c100 else 0.0,
                'feeds_lt100': self.c[('<100', 'feeds')], 'calls_lt100': c100, 'buckets': buckets,
                'insn_max': max(self.insn) if self.insn else 0}


def play(job):
    """One game -> JSON-ready dict.  job: stage, mix (tuple of names, focus first), rot, seed, ticks, size, fixed, duel."""
    names = list(job['mix'])
    r = job['rot']
    slots = [None] * len(names)
    order = names[:]
    # focus (names[0]) in slot r, the others keep their relative order in the remaining slots
    others = names[1:]
    k = 0
    for s in range(len(names)):
        if s == r % len(names):
            slots[s] = names[0]
        else:
            slots[s] = others[k]
            k += 1
    seat = slots.index(names[0])
    pols = [policy(n) for n in slots]
    meter = Meter(seat, pols[seat])
    pols[seat] = meter.policy
    kw = dict(width=job['size'], height=job['size'], seed=job['seed'], max_ticks=job['ticks'])
    if job.get('duel'):
        eng = E.Engine(pols, place_start=False, **kw)
        for y in range(job['size']):
            for x in range(job['size']):
                eng.add_cell(x, y, 0 if x < DUEL_SIDE else 1, 50)
    elif job.get('fixed'):
        eng = E.Engine(pols, start_mode='fixed', start_positions=[FIXED_STARTS[(s + r) % 4] for s in range(len(pols))], **kw)
    else:
        eng = E.Engine(pols, start_mode='random', **kw)
    meter.attach(eng)
    t0 = time.perf_counter()
    while True:
        more = eng.step()
        meter.after_tick()
        if not more:
            break
    secs = time.perf_counter() - t0
    rank = eng.ranking()
    places = {x['colony']: x for x in rank}
    out = {'key': job_key(job), 'stage': job['stage'], 'mix': job['mixname'], 'seed': job['seed'], 'rot': r, 'slots': slots,
           'seat': seat, 'ticks': job['ticks'], 'ticks_run': eng.tick, 'secs': round(secs, 1),
           'place': places[seat]['place'], 'points': places[seat]['points'], 'cells': [places[c]['pop'] for c in range(len(slots))],
           'places': [places[c]['place'] for c in range(len(slots))],
           'faults': {slots[c]: places[c]['faults'] for c in range(len(slots)) if places[c]['faults']},
           'focus_faults': sum(places[seat]['faults'].values()), 'max_insn': places[seat]['max_insn']}
    out.update(meter.result())
    return out


def job_key(j):
    return '%s/%s/%d/%d' % (j['stage'], j['mixname'], j['seed'], j['rot'])


def jobs_for(stage, seeds):
    jobs = []

    def add(stage_, mixname, mix, size, ticks, fixed=False, duel=False, seed_list=None, rots=(0, 1, 2, 3)):
        for seed in (seed_list or seeds):
            for rot in rots:
                jobs.append({'stage': stage_, 'mixname': mixname, 'mix': tuple(mix), 'size': size, 'ticks': ticks,
                             'fixed': fixed, 'duel': duel, 'seed': seed, 'rot': rot})
    if stage == 'm16':
        add('m16', 'A16', ('dogma', 'm353', 'bane22', 'rsiectf'), 16, 500)
        add('m16', 'A16c', ('m353', 'dep_c4d', 'bane22', 'rsiectf'), 16, 500)
    elif stage == 'm64':
        add('m64', 'A', MIXES['A'], 64, 3000)
        add('m64', 'B', MIXES['B'], 64, 3000)
        add('m64', 'Bc', MIXES['Bc'], 64, 3000)
        add('m64', 'C', MIXES['C'], 64, 3000, fixed=True)
        add('m64', 'Cc', MIXES['Cc'], 64, 3000, fixed=True)
    elif stage == 'duel':
        for opp in ('rsiectf', 'm353', 'bane22', 'dep_c4d', 'rvarsi', 'ratompush'):
            add('duel', 'D-dogma-v-' + opp, ('dogma', opp), 16, 3000, duel=True, seed_list=(1,), rots=(0, 1))
        add('duel', 'D-m353-v-rsiectf', ('m353', 'rsiectf'), 16, 3000, duel=True, seed_list=(1,), rots=(0, 1))
        add('duel', 'D-dep_c4d-v-rsiectf', ('dep_c4d', 'rsiectf'), 16, 3000, duel=True, seed_list=(1,), rots=(0, 1))
    elif stage == 'abl':
        for ab in ABLATIONS:
            add('abl', 'A:' + ab, ('dogma:' + ab,) + MIXES['A'][1:], 64, 3000, seed_list=seeds[:2])
            add('abl', 'B:' + ab, ('dogma:' + ab,) + MIXES['B'][1:], 64, 3000, seed_list=seeds[:2])
    return jobs


def load_log(path):
    done = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    done[r['key']] = r
                except ValueError:
                    pass
    return done


def run_stage(stage, seeds, workers, out_dir, report_only=False):
    os.makedirs(out_dir, exist_ok=True)
    log = os.path.join(out_dir, stage + '.jsonl')
    jobs = jobs_for(stage, seeds)
    done = load_log(log)
    todo = [j for j in jobs if job_key(j) not in done]
    print('%s: %d games, %d done, %d to play, %d workers (normal priority)' % (stage, len(jobs), len(done), len(todo), workers), flush=True)
    if todo and not report_only:
        t0 = time.time()
        with multiprocessing.Pool(workers) as pool, open(log, 'a', buffering=1) as f:
            for k, r in enumerate(pool.imap_unordered(play, todo), 1):
                f.write(json.dumps(r) + '\n')
                done[r['key']] = r
                print('  [%d/%d] %s place %d cells %s %.0fs (elapsed %.0fs)' % (k, len(todo), r['key'], r['place'], r['cells'], r['secs'], time.time() - t0), flush=True)
    rows = [done[job_key(j)] for j in jobs if job_key(j) in done]
    report(stage, rows, out_dir)


def report(stage, rows, out_dir):
    L = ['# Dogma local gauntlet: stage %s  (%d games)' % (stage, len(rows)),
         '', 'Local pass bars only measure what the simulator can see (our own cells + calibrated rival models); they do not show Dogma beats the #1 ladder rival.', '']
    by = collections.defaultdict(list)
    for r in rows:
        by[r['mix']].append(r)
    L.append('| mix | games | wins (place 1) | avg place | avg points | focus faults | lock cells | lock cell-ticks | 48/50 alternation cell-ticks | arm@50 calls | t<100 feed % | avg final cells (focus) |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for mix, rs in sorted(by.items()):
        n = len(rs)
        L.append('| %s | %d | %d | %.2f | %.2f | %d | %d | %d | %d | %d | %.4f | %.0f |' % (
            mix, n, sum(r['place'] == 1 for r in rs), sum(r['place'] for r in rs) / n, sum(r['points'] for r in rs) / n,
            sum(r['focus_faults'] for r in rs), sum(r['lock_cells'] for r in rs), sum(r['lock_cell_ticks'] for r in rs), sum(r['alt_cell_ticks'] for r in rs), sum(r['arm50_calls'] for r in rs),
            100.0 * sum(r['feeds_lt100'] for r in rs) / max(1, sum(r['calls_lt100'] for r in rs)),
            sum(r['cells'][r['seat']] for r in rs) / n))
    L += ['', '## Per-window (focus colony, summed over games)', '',
          '| mix | window | calls | feeds | eats enemy | eats friend | stuns | births | deaths |', '|---|---|---|---|---|---|---|---|---|']
    for mix, rs in sorted(by.items()):
        for w in ('<100', '100-300', '300-1000', '1000+'):
            bs = [r['buckets'][w] for r in rs if w in r['buckets']]
            if bs:
                L.append('| %s | %s | %d | %d | %d | %d | %d | %d | %d |' % (
                    mix, w, sum(b['calls'] for b in bs), sum(b['feed_calls'] for b in bs), sum(b['eats_enemy'] for b in bs),
                    sum(b['eats_friend'] for b in bs), sum(b['stuns'] for b in bs), sum(b['births'] for b in bs), sum(b['deaths'] for b in bs)))
    L += ['', '## Faults of any colony (name: kinds)']
    nf = 0
    for r in rows:
        if r['faults']:
            nf += 1
            L.append('- %s: %s' % (r['key'], r['faults']))
    if not nf:
        L.append('- none')
    L += ['', '## Seconds per game: mean %.0f, max %.0f' % (sum(r['secs'] for r in rows) / max(1, len(rows)), max([r['secs'] for r in rows] or [0]))]
    text = '\n'.join(L) + '\n'
    with open(os.path.join(out_dir, stage + '-report.md'), 'w', newline='\n') as f:
        f.write(text)
    print(text, flush=True)


# ---------------------------------------------------------------------------------------------------------------
def _solo(args):
    name, start = args
    pol = policy(name)
    eng = E.Engine([pol], seed=3, max_ticks=100, start_mode='fixed', start_positions=[start])
    pops = {}
    while eng.step():
        pops[eng.tick] = eng.pop[0]
    pops[eng.tick] = eng.pop[0]
    return name, start, [pops.get(t, pops[max(pops)]) for t in (20, 30, 40, 50, 60, 100)]


def run_solo(workers, out_dir):
    """11 real start squares of the m-solo-matrix; Dogma and Bane v2.2 alone; flags every tick where Dogma < v2.2."""
    sys.path.insert(0, os.path.join(ROOT, 'data', 'evidence-2026-11-12', 'scripts'))
    argv = list(sys.argv)
    sys.argv = [argv[0], ROOT, 'unused']
    import solo_starts as SS
    sys.argv = argv
    starts = [(grp, spec, SS.start_of(spec)) for grp, specs in SS.GAMES.items() for spec in specs]
    uniq = sorted({s for _, _, s in starts})
    jobs = [(n, s) for n in ('bane22', 'dogma') for s in uniq]
    with multiprocessing.Pool(workers) as pool:
        res = {(n, s): p for n, s, p in pool.map(_solo, jobs)}
    ticks = (20, 30, 40, 50, 60, 100)
    L = ['# Dogma solo matrix (11 sampled starts, one colony alone, 100 ticks)', '', 'cells at t%s' % '/'.join(map(str, ticks)), '']
    reg = []
    for grp, spec, s in starts:
        b, d = res[('bane22', s)], res[('dogma', s)]
        L.append('%s %s start %s\n  bane22 %s\n  dogma  %s' % (grp, spec, s, b, d))
        bad = [(t, dv, bv) for t, dv, bv in zip(ticks, d, b) if dv < bv]
        if bad:
            reg.append((spec, bad))
    L += ['', 'Starts with any tick below v2.2: %d / %d (gate: 0)' % (len(reg), len(starts))]
    for spec, bad in reg:
        L.append('  %s: %s' % (spec, ['t%d %d < %d (%+.1f%%)' % (t, dv, bv, 100.0 * (dv - bv) / bv) for t, dv, bv in bad]))
    text = '\n'.join(L) + '\n'
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'solo-report.md'), 'w', newline='\n') as f:
        f.write(text)
    print(text, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--stage', choices=('solo', 'm16', 'm64', 'duel', 'abl', 'all'), required=True)
    ap.add_argument('--seeds', default='1-4')
    ap.add_argument('--workers', type=int, default=MAX_WORKERS)
    ap.add_argument('--out', default=OUT_DIR)
    ap.add_argument('--report-only', action='store_true')
    a = ap.parse_args()
    workers = max(1, min(MAX_WORKERS, a.workers))
    seeds = parse_seeds(a.seeds)
    stages = ('solo', 'm16', 'm64', 'duel', 'abl') if a.stage == 'all' else (a.stage,)
    for st in stages:
        if st == 'solo':
            run_solo(workers, a.out)
        else:
            run_stage(st, seeds, workers, a.out, a.report_only)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
