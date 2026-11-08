"""CellHack2 simulator runner.

Examples (from sim/):
  python run.py                                   # hunter, medic, random, walker; seed 1; 64x64; 3000 ticks
  python run.py --bots hunter,idle,medic,walker --seeds 1-20
  python run.py --bots hunter,walker --size 32 --ticks 500 --csv out.csv --snap out.txt --snap-every 100
  python run.py --bots mypolicies:greedy,hunter   # module:function loads your own policy
  python run.py --bots rpump[pump_min=12],ratompush,sprint --start corner

Starts are random squares by default (the ladder, verified 2026-11-08); --start corner is the old model.

With several seeds the slots rotate (game g puts bot (s + g) mod n in slot s) so corner and
slot-number effects average out.  Use --no-rotate to keep the order fixed.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine as E  # noqa: E402
import policies  # noqa: E402

LETTERS = 'ABCD'


def load_policy(spec):
    try:
        return policies.get(spec)
    except KeyError:
        raise SystemExit('unknown policy %r (known: %s, name[k=v,...] or module:function)'
                         % (spec, ', '.join(policies.known())))


def parse_seeds(text):
    seeds = []
    for part in text.split(','):
        if '-' in part:
            a, b = part.split('-')
            seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(part))
    return seeds


def ascii_board(eng):
    W, H = eng.W, eng.H
    rows = [['.'] * W for _ in range(H)]
    for i, x, y, c, e in eng.cells():
        ch = LETTERS[c]
        rows[y][x] = ch if e >= 25 else ch.lower()
    return '\n'.join(''.join(r) for r in rows)


def suffixed(path, seed, many):
    if not many or path is None:
        return path
    root, ext = os.path.splitext(path)
    return '%s_s%d%s' % (root, seed, ext)


def play(names, seed, args, csv_path=None, snap_path=None):
    eng = E.Engine([load_policy(n) for n in names], seed=seed, **engine_kwargs(args))
    csvf = open(csv_path, 'w', newline='') if csv_path else None
    snapf = open(snap_path, 'w') if snap_path else None
    try:
        def record():
            if csvf:
                csvf.write('%d,%s,%s\n' % (eng.tick, ','.join(map(str, eng.pop)), ','.join(map(str, eng.energy))))
            if snapf and (eng.tick % args.snap_every == 0 or eng.finished):
                snapf.write('tick %d  pop %s  energy %s\n%s\n\n' % (eng.tick, eng.pop, eng.energy, ascii_board(eng)))
        if csvf:
            csvf.write('tick,pop0,pop1,pop2,pop3,energy0,energy1,energy2,energy3\n')
        record()
        t0 = time.perf_counter()
        more = True
        while more:
            more = eng.step()
            record()            # row "tick N" = state after N ticks; tick 0 = start
        secs = time.perf_counter() - t0
    finally:
        if csvf:
            csvf.close()
        if snapf:
            snapf.close()
    return eng, eng.ranking(), secs


def fmt_faults(f):
    return ','.join('%s:%d' % kv for kv in sorted(f.items())) or '-'


def print_match(names, eng, res, secs):
    print('seed %d  %dx%d  ticks run %d/%d  %.1fs  order: %s  start %s %s  stun memory %s  '
          'feed bonus %d  idle gain %g'
          % (eng.seed, eng.W, eng.H, eng.tick, eng.max_ticks, secs,
             'no taken jumps' if eng.order_by_alt else 'all instructions', eng.start_mode,
             ' '.join('%d:(%d,%d)' % (c, x, y) for c, (x, y) in sorted(eng.start_positions.items())),
             'keep' if eng.stun_keeps_memory else 'drop', eng.feed_bonus, eng.idle_gain_prob))
    print('%-3s %-4s %-10s %3s %5s %6s %10s %6s %4s %6s %6s %6s %5s  %s'
          % ('pl', 'slot', 'bot', 'pts', 'pop', 'energy', 'insn_total', 'avg', 'max', 'births', 'deaths',
             'stuns', 'died', 'faults'))
    for r in res:
        c = r['colony']
        print('%-3d %-4s %-10s %3d %5d %6d %10d %6.2f %4d %6d %6d %6d %5s  %s'
              % (r['place'], '%d%s' % (c, LETTERS[c]), names[c], r['points'], r['pop'], r['energy'],
                 r['insn_total'], r['avg_insn'], r['max_insn'], r['births'], r['deaths'], r['stuns'],
                 '-' if r['death_tick'] is None else r['death_tick'], fmt_faults(r['faults'])))


def add_engine_args(ap):
    """Engine options shared by run.py and experiments.py."""
    ap.add_argument('--size', type=int, default=None, help='square board side (sets width and height)')
    ap.add_argument('--width', type=int, default=64)
    ap.add_argument('--height', type=int, default=64)
    ap.add_argument('--ticks', type=int, default=3000)
    ap.add_argument('--inset', type=int, default=0, help='start squares inset from the corners (unverified)')
    ap.add_argument('--split-rounding', choices=('floor', 'ceil'), default='floor',
                    help="child's share of a split (unverified)")
    ap.add_argument('--cap-mid-tick', action='store_true', help='clamp energy to 50 at every gain (unverified)')
    ap.add_argument('--order-no-taken-jumps', action='store_true',
                    help='order turns by the policy\'s optional 3rd count (taken jumps not counted); '
                         'totals, averages and the budget still use the full count')
    ap.add_argument('--start', choices=E.START_MODES[:2], default='random',
                    help='start squares: random (ladder, verified 2026-11-08; default) or corner (old model)')
    ap.add_argument('--min-dist', type=int, default=E.DEFAULT_START_MIN_DIST,
                    help='random starts: minimum distance between start squares')
    ap.add_argument('--metric', choices=('manhattan', 'chebyshev'), default=E.DEFAULT_START_METRIC,
                    help='random starts: distance metric for --min-dist')
    ap.add_argument('--sampler', default='uniform', choices=sorted(E.START_SAMPLERS),
                    help='random starts: distribution (engine.START_SAMPLERS)')
    ap.add_argument('--stun-memory', choices=('keep', 'drop'), default='keep',
                    help='whether a stunned cell\'s memory writes persist (unverified; keep = old model)')
    ap.add_argument('--feed-bonus', type=int, default=0,
                    help='extra energy a fed cell gains on top of the 2 fed (ladder receivers often end +3; '
                         'cause unknown; default 0)')
    ap.add_argument('--idle-gain', type=float, default=0.0,
                    help='probability that a cell with no event and no REST gains +1 in a tick (ladder: about '
                         '8%% of no-event cell-ticks end +1, cause unknown; default 0)')


def engine_kwargs(args):
    """Engine keyword arguments from parsed add_engine_args options."""
    w, h = (args.size, args.size) if args.size else (args.width, args.height)
    return dict(width=w, height=h, max_ticks=args.ticks, start_inset=args.inset,
                split_child_rounding=args.split_rounding, cap_mid_tick=args.cap_mid_tick,
                order_by_alt=args.order_no_taken_jumps, start_mode=args.start,
                feed_bonus=args.feed_bonus, idle_gain_prob=args.idle_gain,
                start_min_dist=args.min_dist, start_metric=args.metric, start_sampler=args.sampler,
                stun_keeps_memory=args.stun_memory == 'keep')


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bots', default='hunter,medic,random,walker',
                    help='comma list, slot order (1-4 entries); policy name (%s), name[k=v,...] or '
                         'module:function' % ', '.join(policies.known()))
    ap.add_argument('--seeds', default='1', help='e.g. 1 or 1-20 or 1,4,9')
    add_engine_args(ap)
    ap.add_argument('--no-rotate', action='store_true')
    ap.add_argument('--csv', help='per-tick CSV (tick, pops, energies); with several seeds _s<seed> is added')
    ap.add_argument('--snap', help='ASCII board snapshots file; with several seeds _s<seed> is added')
    ap.add_argument('--snap-every', type=int, default=500)
    ap.add_argument('--verbose', action='store_true', help='print every match table in a series')
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.size:
        args.width = args.height = args.size
    base = policies.split_specs(args.bots)
    if not 1 <= len(base) <= 4:
        raise SystemExit('1 to 4 bots')
    seeds = parse_seeds(args.seeds)
    many = len(seeds) > 1

    agg = {}
    t_all = time.perf_counter()
    for g, seed in enumerate(seeds):
        k = 0 if args.no_rotate else g % len(base)
        names = base[k:] + base[:k]
        eng, res, secs = play(names, seed, args, suffixed(args.csv, seed, many), suffixed(args.snap, seed, many))
        if not many or args.verbose:
            print_match(names, eng, res, secs)
        else:
            print('seed %-4d %5.1fs  ' % (seed, secs) +
                  '  '.join('%d.%s(%d)' % (r['place'], names[r['colony']], r['pop']) for r in res))
        for r in res:
            a = agg.setdefault(names[r['colony']], {'games': 0, 'points': 0, 'wins': 0, 'place': 0,
                                                    'pop': 0, 'faults': 0})
            a['games'] += 1
            a['points'] += r['points']
            a['wins'] += r['place'] == 1
            a['place'] += r['place']
            a['pop'] += r['pop']
            a['faults'] += sum(r['faults'].values())
    if many:
        print('\n%d games, %.1fs total' % (len(seeds), time.perf_counter() - t_all))
        print('%-10s %5s %6s %7s %5s %9s %8s %6s' % ('bot', 'games', 'points', 'pts/gm', 'wins', 'avg place',
                                                    'avg pop', 'faults'))
        for name, a in sorted(agg.items(), key=lambda kv: (-kv[1]['points'], kv[0])):
            n = a['games']
            print('%-10s %5d %6d %7.2f %5d %9.2f %8.1f %6d' % (name, n, a['points'], a['points'] / n, a['wins'],
                                                               a['place'] / n, a['pop'] / n, a['faults']))


if __name__ == '__main__':
    main()
