"""Scratch (review R2; solo engine only, no rival models): opening variants from the 11 sampled start squares.
Variants: v2.2 (cells_ref.bane2); 'first 8/2 dir-open' (first child long 8, later 2, emptiest side first);
'open-long 16/2 sparse-stop 4' (open-space long 16/2, stop after 4 steps with no friend in view); both from
tools/search/opening_search.py.  Per start and variant: cells at t20 / 30 / 40 / 50 / 60 / 100; boxed share of
cell-ticks in windows a (t < 30) and b (30-60); far open eligible 'none' share (open, energy >= 5, no split, move or
feed: position unchanged and energy not lower) in windows a and b.  Every start and tick where a variant has fewer
cells than v2.2 is flagged.
Usage: python solo_matrix.py <repo root> <out.txt> [procs]
"""
import collections
import os
import sys
from multiprocessing import Pool

ROOT = sys.argv[1]
TICKS = (20, 30, 40, 50, 60, 100)
VARIANTS = (('v2.2', None),
            ('first 8/2 dir-open', dict(dir_rule='open')),
            ('open-long 16/2 sparse-stop 4', dict(long_rule='open', dir_rule='open', kl=16, stop='sparse', smin=4)))


def run(args):
    name, kw, start = args
    sys.path.insert(0, os.path.join(ROOT, 'sim'))
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'search'))
    import engine as E
    import cells_ref
    if kw is None:
        pol = cells_ref.bane2
    else:
        sys.argv = [sys.argv[0], ROOT]               # opening_search reads ROOT from argv at import
        import opening_search as OS
        pol = OS.make(**kw)
    eng = E.Engine([pol], seed=3, max_ticks=max(TICKS), start_mode='fixed', start_positions=[start])
    pops = {}
    c = collections.Counter()
    while True:
        t = eng.tick
        w = 'a' if t < 30 else 'b' if t < 60 else None
        before = {}
        if w:
            for i, alive in enumerate(eng.c_alive):
                if not alive:
                    continue
                q, e = eng.c_pos[i], eng.c_en[i]
                opn = any(eng.grid[q + d] == E.GRID_EMPTY for d in eng.dirs)
                c[(w, 'ticks')] += 1
                c[(w, 'boxed')] += not opn
                if opn and e >= 5:
                    before[i] = (q, e)
        if not eng.step():
            break
        pops[eng.tick] = eng.pop[0]
        for i, (q, e) in before.items():
            c[(w, 'elig')] += 1
            c[(w, 'none')] += eng.c_alive[i] and eng.c_pos[i] == q and eng.c_en[i] >= e
    pops[eng.tick] = eng.pop[0]
    st = [100.0 * c[(w, 'boxed')] / max(c[(w, 'ticks')], 1) for w in 'ab'] + \
         [100.0 * c[(w, 'none')] / max(c[(w, 'elig')], 1) for w in 'ab']
    return name, start, [pops.get(t, pops[max(pops)]) for t in TICKS], st


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    argv = list(sys.argv)
    sys.argv = [argv[0], ROOT, 'unused']
    import solo_starts as SS
    sys.argv = argv
    starts = [(grp, spec, SS.start_of(spec)) for grp, specs in SS.GAMES.items() for spec in specs]
    jobs = [(n, kw, s) for n, kw in VARIANTS for s in sorted({s for _, _, s in starts})]
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 2) as pool:
        res = {(n, s): (pops, st) for n, s, pops, st in pool.map(run, jobs)}
    L = []
    L.append('Solo matrix: cells at t%s | boxed %% a / b | far open e>=5 none %% a / b' % '/'.join(map(str, TICKS)))
    flags = []
    for grp, spec, s in starts:
        L.append('%s %s start %d,%d' % (grp, spec, s[0], s[1]))
        base = res[('v2.2', s)][0]
        for n, _ in VARIANTS:
            pops, st = res[(n, s)]
            L.append('  %-30s %s | %5.1f / %5.1f | %5.1f / %5.1f' % (n, ' '.join('%5d' % v for v in pops), *st))
            if n != 'v2.2':
                for t, v, b in zip(TICKS, pops, base):
                    if v < b:
                        flags.append('%s %s %s t%d: %d < v2.2 %d (%+.1f%%)' % (grp, spec, n, t, v, b, 100.0 * (v - b) / b))
    L.append('\nMeans by group (cells at each tick; boxed a / b; none a / b)')
    for grp in SS.GAMES:
        ss = [s for g, _, s in starts if g == grp]
        for n, _ in VARIANTS:
            P = [res[(n, s)][0] for s in ss]
            S_ = [res[(n, s)][1] for s in ss]
            L.append('%-5s %-30s %s | %5.1f / %5.1f | %5.1f / %5.1f' % (
                grp, n, ' '.join('%5.0f' % (sum(p[i] for p in P) / len(P)) for i in range(len(TICKS))),
                *(sum(x[i] for x in S_) / len(S_) for i in range(4))))
    L.append('\nFlags (variant below v2.2): %d' % len(flags))
    L += flags
    open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
