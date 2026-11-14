"""Misfortune test runner (briefs/misfortune-spec-2026-11-13.md): our own reference cells only, no rival model.

Line-up: the subject (Misfortune, or the control Bane v2.3a) in one seat; Bane v2.2, Conviction and Penalty in the other
three, in that order.  Seat = (seed - 1) mod 4; the control plays the same seed and seat.  Random starts.

Stages (each one unattended command, run from sim/):
  python misfortune_runner.py --stage 1             # cap screen: caps A, B (exact 1) + control, seeds 1-4, 1000 ticks
  python misfortune_runner.py --stage 1n            # only if both caps are out: cap N on the same 4 seeds
  python misfortune_runner.py --stage 2             # pass bar: chosen cap + control, seeds 1-8, 3000 ticks
  python misfortune_runner.py --stage 2 --extra     # 8 more seeds (9-16) when a first-two-lines result is exactly 6/8
  python misfortune_runner.py --stage 3             # side checks, seeds 1-2, 1000 ticks: exact 0; capmid on (+ control)
Stages 2 and 3 take the cap chosen by the Stage 1 log; --cap overrides it.
Each finished game appends one JSON line to <out>/stage<N>.jsonl; a restart skips the games already in it.
The report (<out>/stage<N>-report.md) leads with the pass-bar or screen table (met / not met per line).
Workers: default 6, at most 6, normal priority (--low-priority lowers it).
"""

import argparse
import collections
import json
import math
import multiprocessing
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cells_ref as C  # noqa: E402
import engine as E  # noqa: E402
import experiments as X  # noqa: E402

OPPONENTS = ('bane22', 'conviction', 'penalty')
CHECK_TICKS = (100, 300, 600, 1000, 2000, 3000)
WINDOWS = ((0, 100, '<100'), (100, 300, '100-300'), (300, 1000, '300-1000'), (1000, 10 ** 9, '1000+'))
HIGH_E = 47
CAP_E = E.ENERGY_MAX
MAX_WORKERS = 6
DEFAULT_WORKERS = 6
BAR_FIRST = {'conviction': 0.90, 'bane22': 0.95}
BAR_FRIENDLY = 1.0       # unintended (armed-slot) friendly bites per 100 enemy bites
BAR_STUCK = 0.05         # failed armed-slot eats per contact cell-tick
STAGE1_SEEDS = (1, 2, 3, 4)
STAGE2_SEEDS = (1, 2, 3, 4, 5, 6, 7, 8)
STAGE2_EXTRA = tuple(range(9, 17))
STAGE3_SEEDS = (1, 2)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'misfortune')
CTRL_STORED_N = 4        # Bane v2.3a's stored bite
KIND = {E.ACT_REST: 'rest', E.ACT_NOP: 'nop'}


def window_of(t):
    for lo, hi, name in WINDOWS:
        if lo <= t < hi:
            return name


def seat_for(seed):
    return (seed - 1) % 4


def subject_policy(variant):
    if variant == 'ctrl':
        return C.make_bane3()
    return C.make_misfortune(cap=variant[0], exact=int(variant[1]))


def other_policy(name):
    return {'bane22': C.make_bane2, 'conviction': C.make_conviction, 'penalty': C.make_penalty}[name]()


class Meter(object):
    """Counters for one subject colony.  Wraps the subject policy (meter.policy) and installs the engine hooks
    (meter.attach(eng)); call meter.after_tick() after every eng.step() and meter.result() at the end."""

    def __init__(self, seat, policy, ctrl=False):
        self.seat = seat
        self.sub = policy
        self.ctrl = ctrl
        self.armed_n = CTRL_STORED_N if ctrl else 2
        self.bite_n = 12 if ctrl else C.MISFORTUNE_BITE_N[(policy.exact, policy.cap)]
        self.calls_now = {}                  # (x, y) -> count of this tick's call
        self.paths = collections.Counter()   # 'label/count/contact' -> calls
        self.contact = 0
        self.contact_e = collections.Counter()      # (window, bucket) -> contact calls; bucket all / 47+ / 49 / 50
        self.contested = collections.Counter()      # (opp colony, window, first 0/1) -> pair-ticks
        self.contested_hi = collections.Counter()   # (opp colony, first 0/1), our energy 47+ at the call
        self.c = collections.Counter()              # plain counters
        self.prev_adj = set()
        self.ev_now = collections.defaultdict(set)
        self.ev_prev = collections.defaultdict(set)
        self.stuck_now = set()
        self.episodes = {}                          # cell id -> length so far
        self.ep_done = []                           # (length, cause)
        self.checks = {}
        self.noop_now, self.noop_runs, self.noop_done = set(), {}, []   # armed-split no-op runs per square
        self.eng = None

        def wrapped(view, mem):
            r = self.sub(view, mem)
            cl = view.cells
            con = any(cl[E.VIEW_DIR[d]] == E.CELL_ENEMY for d in range(4))
            n, a = r[1], r[0]
            self.calls_now[(view.x, view.y)] = n
            if n == 2 and a & 0xF0 == E.ACT_SPLIT:        # armed SPLIT (Depravity): no-op when the square is taken
                self.c['armed_splits'] += 1
                if view.cells[E.VIEW_DIR[a & 3]] != E.CELL_EMPTY:
                    self.c['armed_split_noop'] += 1
                    self.noop_now.add((view.x, view.y))
            if con:
                self.contact += 1
                w = window_of(view.tick)
                e = view.energy
                self.contact_e[(w, 'all')] += 1
                if e >= HIGH_E:
                    self.contact_e[(w, '47+')] += 1
                if e in (49, 50):
                    self.contact_e[(w, str(e))] += 1
            self.paths['%s/%d/%d' % (self.label(a, n, con), n, int(con))] += 1
            return r
        self.policy = wrapped

    def label(self, a, n, con):
        k = a & 0xF0
        if n == self.armed_n and k == E.ACT_EAT:
            return 'stored' if self.ctrl else 'armed'
        if con and n == self.bite_n and k == E.ACT_EAT:
            return 'scan' if self.ctrl else 'arming'
        if not self.ctrl and n == C.MISFORTUNE_PULL_N:
            return 'pull' if k == E.ACT_EAT else 'lift'
        return KIND.get(a, {E.ACT_MOVE: 'move', E.ACT_SPLIT: 'split', E.ACT_EAT: 'eat', E.ACT_FEED: 'feed'}.get(k, '?'))

    def attach(self, eng):
        self.eng = eng
        eng.order_hook = self.on_order
        eng.act_hook = self.on_act

    def _xy(self, i):
        p = self.eng.c_pos[i]
        return p % self.eng.PW - 2, p // self.eng.PW - 2

    def on_order(self, t, acts):
        eng, seat = self.eng, self.seat
        col, pos, grid, alive, en, dirs = eng.c_col, eng.c_pos, eng.grid, eng.c_alive, eng.c_en, eng.dirs
        rank = {}
        act = {}
        for k, (_, i, a) in enumerate(acts):
            rank[i] = k
            act[i] = a
        w = window_of(t)
        cur = set()
        prev = self.prev_adj
        for i in eng.live:
            if col[i] != seat or not alive[i]:
                continue
            p = pos[i]
            for o in dirs:
                g = grid[p + o]
                if g >= 0 and alive[g] and col[g] != seat:
                    cur.add((i, g))
            a = act.get(i)
            if a is None or a & 0xF0 != E.ACT_EAT:
                continue
            g = grid[p + dirs[a & 3]]
            if g < 0 or col[g] == seat or (i, g) not in prev:
                continue
            b = act.get(g)
            if b is None or b & 0xF0 != E.ACT_EAT or pos[g] + dirs[b & 3] != p:
                continue
            first = int(rank[i] < rank[g])
            self.contested[(col[g], w, first)] += 1
            if en[i] >= HIGH_E:
                self.contested_hi[(col[g], first)] += 1
        self.prev_adj = cur

    def on_act(self, t, i, a, g):
        eng, seat = self.eng, self.seat
        col, en = eng.c_col, eng.c_en
        eat = a & 0xF0 == E.ACT_EAT
        if col[i] == seat:
            n = self.calls_now.get(self._xy(i))
            if eat and n == self.armed_n:
                self.c['armed_eats'] += 1
                if g < 0:
                    self.c['armed_fail'] += 1
                    self.stuck_now.add(i)
                elif col[g] == seat:
                    self.c['armed_friend'] += 1
                    self.ev_now[i].add('friend_refill')
                else:
                    self.c['armed_enemy'] += 1
                    self.ev_now[i].add('enemy_refill')
            elif eat and g >= 0 and col[g] == seat:
                if not self.ctrl and n == C.MISFORTUNE_PULL_N:
                    self.c['pulls'] += 1
                    self.c['pull_cap_loss'] += max(0, en[i] + min(E.EAT_TAKE, en[g]) - CAP_E)
                    self.ev_now[g].add('pull')
                else:
                    self.c['other_friend_eats'] += 1
            elif not eat and g >= 0:
                if not self.ctrl and n == C.MISFORTUNE_PULL_N:
                    self.c['lifts'] += 1
                self.ev_now[g].add('feed')
        elif eat and g >= 0 and col[g] == seat:
            self.ev_now[g].add('bitten')

    def after_tick(self):
        eng = self.eng
        t = eng.tick
        alive = eng.c_alive
        for i in self.stuck_now:
            self.episodes[i] = self.episodes.get(i, 0) + 1
        for i in [k for k in self.episodes if k not in self.stuck_now]:
            now, prev = self.ev_now.get(i, ()), self.ev_prev.get(i, ())
            for cause in ('enemy_refill', 'friend_refill', 'feed', 'bitten', 'pull'):
                if cause in now or cause in prev:
                    break
            else:
                cause = 'other' if (i < len(alive) and alive[i]) else 'died'
            self.ep_done.append((self.episodes.pop(i), cause))
        for k in list(self.noop_runs):
            if k not in self.noop_now:
                self.noop_done.append(self.noop_runs.pop(k))
        for k in self.noop_now:
            self.noop_runs[k] = self.noop_runs.get(k, 0) + 1
        self.noop_now = set()
        self.stuck_now = set()
        self.ev_prev, self.ev_now = self.ev_now, collections.defaultdict(set)
        self.calls_now = {}
        if t in CHECK_TICKS:
            self.checks[t] = (list(eng.pop), list(eng.energy))

    def result(self):
        eng, seat = self.eng, self.seat
        for i, n in self.episodes.items():
            self.ep_done.append((n, 'open_at_end'))
        self.episodes = {}
        out = dict(self.c)
        for k in ('armed_eats', 'armed_fail', 'armed_friend', 'armed_enemy', 'pulls', 'pull_cap_loss', 'lifts',
                  'other_friend_eats'):
            out.setdefault(k, 0)
        out['contact_ticks'] = self.contact
        out['eats_enemy'], out['eats_friend'] = eng.eats_enemy[seat], eng.eats_friend[seat]
        out['paths'] = dict(self.paths)
        out['contact_energy'] = {'%s|%s' % k: v for k, v in self.contact_e.items()}
        out['contested'] = {'%d|%s|%d' % k: v for k, v in self.contested.items()}
        out['contested_hi'] = {'%d|%d' % k: v for k, v in self.contested_hi.items()}
        out['episodes'] = [list(x) for x in self.ep_done]
        final = (list(eng.pop), list(eng.energy))
        out['checks'] = {str(t): self.checks.get(t, final) for t in CHECK_TICKS}
        kills = [r for r in (eng.race_rows() or []) if r[2] == seat and r[1] != seat]
        f = collections.Counter()
        for r in kills:
            fill, dt = r[4], r[5]
            if fill == seat and dt <= 1:
                f['us_t1'] += 1
            if fill == seat and dt <= 5:
                f['us_t5'] += 1
            elif fill >= 0 and dt <= 5:
                f['enemy_t5'] += 1
            else:
                f['empty_t5'] += 1
        for r in kills:
            if r[4] >= 0 and r[4] != seat and r[5] <= 1:
                f['enemy_t1'] += 1
        out['freed'] = dict(f, kills=len(kills))
        out['noop_runs'] = self.noop_done + list(self.noop_runs.values())
        for k in ('armed_splits', 'armed_split_noop'):
            out.setdefault(k, 0)
        return out


def job_key(job):
    return '%s|%d|%d|%d|%d' % (job['variant'], job['seed'], job['seat'], int(job['capmid']), job['ticks'])


def play(job):
    """One game: a JSON-ready dict."""
    seat = job['seat']
    ctrl = job['variant'] == 'ctrl'
    names = list(OPPONENTS)
    names.insert(seat, 'v2.3a' if ctrl else 'misfortune-%s' % job['variant'])
    meter = Meter(seat, subject_policy(job['variant']), ctrl=ctrl)
    pols = [other_policy(n) for n in OPPONENTS]
    pols.insert(seat, meter.policy)
    eng = E.Engine(pols, seed=job['seed'], max_ticks=job['ticks'], start_mode='random',
                   cap_mid_tick=bool(job['capmid']), record_races=True)
    meter.attach(eng)
    t0 = time.perf_counter()
    secs_at = {}
    while True:
        more = eng.step()
        meter.after_tick()
        if eng.tick in CHECK_TICKS:
            secs_at[str(eng.tick)] = round(time.perf_counter() - t0, 2)
        if not more:
            break
    secs = time.perf_counter() - t0
    places = {r['colony']: r['place'] for r in eng.ranking()}
    out = {'key': job_key(job), 'variant': job['variant'], 'seed': job['seed'], 'seat': seat,
           'capmid': int(job['capmid']), 'ticks': job['ticks'], 'ticks_run': eng.tick, 'names': names,
           'places': [places[c] for c in range(4)], 'place': places[seat], 'cells': eng.pop[seat],
           'secs': round(secs, 2), 'secs_at': secs_at}
    out.update(meter.result())
    return out


# ---- stages ----------------------------------------------------------------------------------------------------
def stage_jobs(stage, cap, extra=False):
    def jobs(variants, seeds, ticks, capmid=0):
        return [{'variant': v, 'seed': s, 'seat': seat_for(s), 'capmid': capmid, 'ticks': ticks}
                for s in seeds for v in variants]
    if stage == '1':
        return jobs(('A1', 'B1', 'ctrl'), STAGE1_SEEDS, 1000)
    if stage == '1n':
        return jobs(('N1',), STAGE1_SEEDS, 1000)
    if stage == '2':
        return jobs((cap + '1', 'ctrl'), STAGE2_SEEDS + (STAGE2_EXTRA if extra else ()), 3000)
    if stage == '3':
        return jobs((cap + '0',), STAGE3_SEEDS, 1000) + jobs((cap + '1', 'ctrl'), STAGE3_SEEDS, 1000, capmid=1)
    raise ValueError(stage)


def read_log(path):
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def run_stage(jobs, log_path, workers, low_priority, progress=print):
    done = {r['key'] for r in read_log(log_path)}
    todo = [j for j in jobs if job_key(j) not in done]
    progress('%d games in the stage, %d already in %s, %d to run on %d workers' % (
        len(jobs), len(jobs) - len(todo), os.path.basename(log_path), len(todo), workers))
    if not todo:
        return
    t0 = time.time()

    def write(r, k):
        with open(log_path, 'a') as f:
            f.write(json.dumps(r, sort_keys=True) + '\n')
        progress('[%d/%d] %s seed %d seat %d capmid %d: place %d, cells %d, %.1f s (wall %.0f s)' % (
            k, len(todo), r['variant'], r['seed'], r['seat'], r['capmid'], r['place'], r['cells'], r['secs'],
            time.time() - t0))
    init = X.lower_priority if low_priority else None
    if workers <= 1 or len(todo) == 1:
        if init:
            init()
        for k, j in enumerate(todo, 1):
            write(play(j), k)
        return
    ctx = multiprocessing.get_context('spawn')
    with ctx.Pool(min(workers, len(todo)), initializer=init) as pool:
        for k, r in enumerate(pool.imap_unordered(play, todo, chunksize=1), 1):
            write(r, k)


# ---- aggregation and report ------------------------------------------------------------------------------------
def opp_colony(r, name):
    return r['names'].index(name)


def contested_of(rows, opp, hi=False):
    n = first = 0
    for r in rows:
        c = opp_colony(r, opp)
        if hi:
            first += r['contested_hi'].get('%d|1' % c, 0)
            n += r['contested_hi'].get('%d|1' % c, 0) + r['contested_hi'].get('%d|0' % c, 0)
        else:
            for k, v in r['contested'].items():
                cc, _, f = k.split('|')
                if int(cc) == c:
                    n += v
                    first += v * int(f)
    return first, n


def _ratio(a, b):
    return (a / b) if b else None


def _pct(x):
    return '-' if x is None else '%.1f%%' % (100 * x)


def friendly_of(rows):
    return _ratio(100.0 * sum(r['armed_friend'] for r in rows), sum(r['eats_enemy'] for r in rows))


def stuck_of(rows):
    return _ratio(sum(r['armed_fail'] for r in rows), sum(r['contact_ticks'] for r in rows))


def screen_lines(rows):
    """[(line, value, met)] of the Stage 1 screen / the mechanism lines of the Stage 2 bar (pooled)."""
    out = []
    fr = friendly_of(rows)
    out.append(('unintended friendly bites <= 1 per 100 enemy bites', '-' if fr is None else '%.2f' % fr,
                fr is not None and fr <= BAR_FRIENDLY))
    s = stuck_of(rows)
    out.append(('stuck <= 5% of contact cell-ticks', _pct(s), s is not None and s <= BAR_STUCK))
    for o, label in (('conviction', 'Conviction'), ('bane22', 'Bane v2.2')):
        f, n = contested_of(rows, o)
        x = _ratio(f, n)
        out.append(('bit first >= %d%% of contested pair-ticks vs %s' % (round(100 * BAR_FIRST[o]), label),
                    '%d/%d = %s' % (f, n, _pct(x)), x is not None and x >= BAR_FIRST[o]))
    return out


def table(lines):
    out = ['| line | value | met |', '|---|---|---|']
    for name, val, met in lines:
        out.append('| %s | %s | %s |' % (name, val, '-' if met is None else ('yes' if met else 'NO')))
    return out


def by_variant(rows):
    d = collections.defaultdict(list)
    for r in rows:
        d[(r['variant'], r['capmid'], r['ticks'])].append(r)
    return d


def cells_at(r, t):
    return r['checks'][str(t)][0][r['seat']]


def stage1_decision(rows):
    """(chosen cap or None, text lines)."""
    g = by_variant(rows)
    ctrl = {r['seed']: r for r in g.get(('ctrl', 0, 1000), [])}
    lines = []
    status = {}
    diffs = {}
    for cap in ('A', 'B'):
        rs = g.get((cap + '1', 0, 1000), [])
        if not rs:
            continue
        ok = all(m for _, _, m in screen_lines(rs))
        status[cap] = ok
        diffs[cap] = {r['seed']: cells_at(r, 1000) - cells_at(ctrl[r['seed']], 1000) for r in rs if r['seed'] in ctrl}
        lines.append('- cap %s: %s; (new - control) cells at t1000 by seed %s, sum %d' % (
            cap, 'in' if ok else 'OUT', ', '.join('%d: %+d' % kv for kv in sorted(diffs[cap].items())),
            sum(diffs[cap].values())))
    inn = [c for c in ('A', 'B') if status.get(c)]
    if len(status) < 2:
        return None, lines + ['- Stage 1 incomplete.']
    if not inn:
        return None, lines + ['- Both caps out: stop, run --stage 1n (cap N on the same seeds), report to the reviewer.']
    if len(inn) == 2:
        sa, sb = sum(diffs['A'].values()), sum(diffs['B'].values())
        per = [diffs['A'][s] - diffs['B'][s] for s in diffs['A'] if s in diffs['B']]
        mixed = any(x > 0 for x in per) and any(x < 0 for x in per)
        cap = 'A' if (sa > sb and not mixed) else 'B'
        lines.append('- Both in: sums A %d, B %d; per-seed A - B %s -> %s%s' % (
            sa, sb, per, cap, ' (tie or mixed sign: B)' if cap == 'B' and (sa == sb or mixed) else ''))
    else:
        cap = inn[0]
        lines.append('- Only cap %s is in.' % cap)
    below = sum(1 for v in diffs[cap].values() if v < 0)
    if below >= 3:
        lines.append('- Cap %s is below the control on %d of 4 seeds at t1000: stop, no Stage 2; report to the reviewer.'
                     % (cap, below))
        return None, lines
    lines.append('- Chosen cap: %s. Next: --stage 2 (and --stage 3 in the same batch).' % cap)
    return cap, lines


def stage2_bar(rows_new, rows_ctrl):
    n = len(rows_new)
    need = math.ceil(7 * n / 8.0)
    ctrl = {r['seed']: r for r in rows_ctrl}
    wins = sum(1 for r in rows_new if r['place'] == 1)
    above = sum(1 for r in rows_new if r['seed'] in ctrl and r['cells'] > ctrl[r['seed']]['cells'])
    lines = [('places first in >= %d of %d games' % (need, n), '%d/%d' % (wins, n), wins >= need),
             ('above paired control (final cells) on >= %d of %d seeds' % (need, n), '%d/%d' % (above, n),
              above >= need)]
    lines += screen_lines(rows_new)
    worst_f = max((friendly_of([r]) or 0) for r in rows_new) if rows_new else None
    worst_s = max((stuck_of([r]) or 0) for r in rows_new) if rows_new else None
    lines.append(('worst single game: unintended friendly per 100 / stuck', '%.2f / %s' % (worst_f or 0,
                  _pct(worst_s)), None))
    more = n == 8 and (wins == 6 or above == 6)
    return lines, more


def mechanism_report(rows, label):
    """Per-opponent and mechanism tables for one variant group."""
    out = ['### %s (%d games)' % (label, len(rows)), '']
    out.append('| opponent | contested pair-ticks | bit first | ' + ' | '.join(w for _, _, w in WINDOWS) +
               ' | our energy 47+ |')
    out.append('|---|---|---|' + '---|' * len(WINDOWS) + '---|')
    for o in OPPONENTS:
        f, n = contested_of(rows, o)
        cells = []
        for _, _, w in WINDOWS:
            ff = nn = 0
            for r in rows:
                c = opp_colony(r, o)
                for fl in (0, 1):
                    v = r['contested'].get('%d|%s|%d' % (c, w, fl), 0)
                    nn += v
                    ff += v * fl
            cells.append('%s (%d)' % (_pct(_ratio(ff, nn)), nn))
        hf, hn = contested_of(rows, o, hi=True)
        out.append('| %s | %d | %s | %s | %s (%d) |' % (o, n, _pct(_ratio(f, n)), ' | '.join(cells),
                                                        _pct(_ratio(hf, hn)), hn))
    out.append('')
    s = collections.Counter()
    for r in rows:
        s.update({k: r[k] for k in ('armed_eats', 'armed_fail', 'armed_friend', 'armed_enemy', 'pulls',
                                    'pull_cap_loss', 'lifts', 'other_friend_eats', 'contact_ticks', 'eats_enemy',
                                    'eats_friend')})
    out.append('Armed-slot eats %d: failed %d (%s of armed eats, %s of %d contact cell-ticks), hit a friend %d '
               '(unintended: %s per 100 enemy bites), hit an enemy %d. Pulls by cap rule %d (energy lost to the cap '
               '%d), lifts %d, other friendly eats %d. Enemy bites %d.' % (
                   s['armed_eats'], s['armed_fail'], _pct(_ratio(s['armed_fail'], s['armed_eats'])),
                   _pct(_ratio(s['armed_fail'], s['contact_ticks'])), s['contact_ticks'], s['armed_friend'],
                   '-' if not s['eats_enemy'] else '%.2f' % (100.0 * s['armed_friend'] / s['eats_enemy']),
                   s['armed_enemy'], s['pulls'], s['pull_cap_loss'], s['lifts'], s['other_friend_eats'],
                   s['eats_enemy']))
    eps = sorted(n for r in rows for n, _ in r['episodes'])
    causes = collections.Counter(c for r in rows for _, c in r['episodes'])
    if eps:
        out.append('Stuck episodes %d: length median %d, p95 %d, max %d; ended by %s.' % (
            len(eps), eps[len(eps) // 2], eps[min(len(eps) - 1, int(0.95 * len(eps)))], eps[-1],
            ', '.join('%s %d' % kv for kv in causes.most_common())))
    out.append('')
    out.append('| window | contact calls | energy 47+ | 49 | 50 |')
    out.append('|---|---|---|---|---|')
    for _, _, w in WINDOWS:
        tot = sum(r['contact_energy'].get('%s|all' % w, 0) for r in rows)
        vals = [sum(r['contact_energy'].get('%s|%s' % (w, b), 0) for r in rows) for b in ('47+', '49', '50')]
        out.append('| %s | %d | %s |' % (w, tot, ' | '.join(_pct(_ratio(v, tot)) for v in vals)))
    out.append('')
    fr = collections.Counter()
    for r in rows:
        fr.update(r['freed'])
    k = fr['kills']
    out.append('Freed squares (we killed the occupant) %d: ours next tick %s, ours within 5 %s, enemy within 5 %s, '
               'empty at 5 %s.' % (k, _pct(_ratio(fr['us_t1'], k)), _pct(_ratio(fr['us_t5'], k)),
                                   _pct(_ratio(fr['enemy_t5'], k)), _pct(_ratio(fr['empty_t5'], k))))
    ticks = [t for t in CHECK_TICKS if t <= rows[0]['ticks']]
    out.append('')
    out.append('| seed | seat | place | ' + ' | '.join('cells t%d' % t for t in ticks) + ' | s/game |')
    out.append('|---|---|---|' + '---|' * len(ticks) + '---|')
    for r in sorted(rows, key=lambda r: r['seed']):
        out.append('| %d | %d | %d | %s | %.0f |' % (r['seed'], r['seat'], r['place'],
                                                     ' | '.join(str(cells_at(r, t)) for t in ticks), r['secs']))
    paths = collections.Counter()
    for r in rows:
        paths.update(r['paths'])
    out.append('')
    out.append('Calls by path (label/count/in contact): ' + ', '.join(
        '%s %d' % kv for kv in sorted(paths.items(), key=lambda kv: -kv[1])[:24]))
    out.append('')
    return out


NOTE = ('Note: bit first >= 90% vs Conviction is necessary, not sufficient. Conviction is our 3-instruction '
        'stand-in; it lacks aimed children and a checked rescan, and no rival model is run. The ladder is the first '
        'test against the rivals themselves.')


def stage_report(stage, rows, cap=None):
    g = by_variant(rows)
    out = ['# Misfortune stage %s report' % stage, '']
    if stage == '1':
        for c in ('A', 'B'):
            rs = g.get((c + '1', 0, 1000))
            if rs:
                out += ['## Screen, cap %s (pooled over %d games)' % (c, len(rs)), ''] + table(screen_lines(rs)) + ['']
        cap_, lines = stage1_decision(rows)
        out += ['## Decision', ''] + lines + ['', NOTE, '']
    elif stage == '2':
        new = g.get((cap + '1', 0, 3000), [])
        ctrl = g.get(('ctrl', 0, 3000), [])
        lines, more = stage2_bar(new, ctrl)
        out += ['## Pass bar, cap %s' % cap, ''] + table(lines) + ['']
        if more:
            out.append('Exactly 6 of 8 on a first-two-lines result: run --stage 2 --extra (8 more seeds).')
        out += [NOTE, '']
    elif stage == '3':
        out += ['## Side checks, cap %s' % cap, '']
        s1 = read_log(os.path.join(OUT_DIR, 'stage1.jsonl'))
        base = [r for r in s1 if r['variant'] == cap + '1' and r['seed'] in STAGE3_SEEDS and r['capmid'] == 0]
        on = g.get((cap + '1', 1, 1000), [])
        if base and on:
            def hi(rs):
                f = n = 0
                for o in ('conviction', 'bane22', 'penalty'):
                    a, b = contested_of(rs, o, hi=True)
                    f, n = f + a, n + b
                return _ratio(f, n)
            hb, ho = hi(base), hi(on)
            sb, so = stuck_of(base), stuck_of(on)
            move = None if hb is None or ho is None else abs(ho - hb) * 100
            flag = (move is not None and move > 5) or (sb and so and so > 2 * sb)
            out.append('capmid on vs off (seeds %s): bit first at 47+ %s -> %s, stuck %s -> %s. %s' % (
                STAGE3_SEEDS, _pct(hb), _pct(ho), _pct(sb), _pct(so),
                'FLAG: ask the user for a site calibration probe before any ladder run.' if flag else 'No flag.'))
        else:
            out.append('capmid comparison needs the Stage 1 games of seeds %s in stage1.jsonl.' % (STAGE3_SEEDS,))
        out.append('exact=0 has no feeder in this line-up, which favours exact=1.')
        out.append('')
    out.append('## Per variant')
    out.append('')
    for (v, cm, ticks), rs in sorted(g.items()):
        out += mechanism_report(rs, '%s, capmid %s, %d ticks' % (v, 'on' if cm else 'off', ticks))
    return '\n'.join(out)


def chosen_cap(out_dir):
    cap, _ = stage1_decision(read_log(os.path.join(out_dir, 'stage1.jsonl')))
    return cap


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--stage', choices=('1', '1n', '2', '3'), required=True)
    ap.add_argument('--cap', choices=('A', 'B', 'N'), default=None, help='stages 2 and 3: override the Stage 1 choice')
    ap.add_argument('--extra', action='store_true', help='stage 2: add seeds 9-16')
    ap.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                    help='worker processes (default %d, at most %d)' % (DEFAULT_WORKERS, MAX_WORKERS))
    ap.add_argument('--low-priority', action='store_true', help='run the workers at below-normal priority')
    ap.add_argument('--out', default=OUT_DIR)
    ap.add_argument('--report-only', action='store_true', help='write the report from the log, play nothing')
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    global OUT_DIR
    OUT_DIR = args.out
    os.makedirs(args.out, exist_ok=True)
    cap = args.cap
    if args.stage in ('2', '3') and cap is None:
        cap = chosen_cap(args.out)
        if cap is None:
            raise SystemExit('No cap chosen by the Stage 1 log; pass --cap to override.')
    name = 'stage%s' % args.stage
    log_path = os.path.join(args.out, name + '.jsonl')
    jobs = stage_jobs(args.stage, cap, args.extra)
    if not args.report_only:
        run_stage(jobs, log_path, max(1, min(MAX_WORKERS, args.workers)), args.low_priority)
    keys = {job_key(j) for j in jobs}
    rows = [r for r in read_log(log_path) if r['key'] in keys]
    if args.stage == '1n':
        text = '# Misfortune stage 1n (cap N)\n\n' + '\n'.join(table(screen_lines(rows)) + ['']) + '\n' + '\n'.join(
            mechanism_report(rows, 'N1, capmid off, 1000 ticks'))
    else:
        text = stage_report(args.stage, rows, cap)
    rp = os.path.join(args.out, name + '-report.md')
    with open(rp, 'w', newline='\n') as f:
        f.write(text + '\n')
    print(text)
    print('\nLog: %s\nReport: %s' % (log_path, rp))


if __name__ == '__main__':
    main()
