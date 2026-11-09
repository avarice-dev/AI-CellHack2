"""Solo growth study (designs.md 10.4 item 1, Schism): our colony alone on the board, no rivals.

Before first contact the simulator models our own colony exactly (no rival model is involved), so the split
direction rule can be compared offline.  Each policy is Complacency (sim/cells_ref.complacency) with only its split
direction (and, for the 'feed' variants, the boxed-cell action) changed while no enemy is in the 5x5 view.

    python sim/growth.py                         # all policies, 50 starts, 200 ticks, one process
    python sim/growth.py --policies a,c --starts 20 --ticks 100

Starts: uniform random squares from random.Random(seed) (a uniform square on 64x64 has a median nearest-edge
distance of about 10, as the real starts do).  Metrics per policy: first tick at pop 128 and 512, and pop at
t25/50/100/200 (median and quartiles).  "pop at tN" is the population after N ticks have run; "first tick at P" is
the number of ticks run when the population first reaches P (so the start cell is tick 0).
One process, below-normal priority.
"""

import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
import cells_ref  # noqa: E402
from engine import ACT_SPLIT, ACT_FEED, ACT_REST, CELL_EMPTY, CELL_FRIEND, CELL_ENEMY, VIEW_DIR  # noqa: E402

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
FIXED = (DOWN, RIGHT, UP, LEFT)                 # Complacency's split order
FEED_ORDER = (UP, RIGHT, DOWN, LEFT)            # Complacency's / Contagion's feed scan order
STEP = {UP: (0, -1), RIGHT: (1, 0), DOWN: (0, 1), LEFT: (-1, 0)}
NB = {UP: 7, RIGHT: 13, DOWN: 17, LEFT: 11}     # view index of the neighbour


def _rc(i):
    return divmod(i, 5)


def _sq(r, c):
    return r * 5 + c


# Squares counted for a candidate neighbour, per counting rule (all inside the 5x5 view; self (12) never empty).
def _ring3x3(d):                    # (b): the neighbour's 3x3 minus itself
    r, c = _rc(NB[d])
    return tuple(_sq(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0))


def _ring4(d):                      # (c): the neighbour's own 4 neighbours (one of them is self)
    r, c = _rc(NB[d])
    return tuple(_sq(r + dr, c + dc) for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)))


def _half(d):                       # own variant: the two rows / columns of the view on that side (10 squares)
    rows = {UP: (0, 1), DOWN: (3, 4)}.get(d, range(5))
    cols = {LEFT: (0, 1), RIGHT: (3, 4)}.get(d, range(5))
    return tuple(_sq(r, c) for r in rows for c in cols)


def _ring4w(d):                     # (c) restricted to view window 6..21 (what one 16-byte load sees: no 2 / 22)
    return tuple(i for i in _ring4(d) if 6 <= i <= 21)


COUNTS = {'b': {d: _ring3x3(d) for d in FIXED}, 'c': {d: _ring4(d) for d in FIXED},
          'h': {d: _half(d) for d in FIXED}, 'w': {d: _ring4w(d) for d in FIXED}}


def _origin(view, mem):
    if not mem[1] & 1:              # first call of the start cell; children copy the memory
        mem[1] |= 1
        mem[2], mem[3] = view.x & 0xFF, view.y & 0xFF
    return mem[2], mem[3]


def _away(view, org, d):
    """> 0 when a step in direction d moves away from the origin (dot product of step and position - origin)."""
    sx, sy = STEP[d]
    return sx * (view.x - org[0]) + sy * (view.y - org[1])


def make_policy(count=None, tie='origin', away_first=False, alt=None, gate1=True, feed=None, feed_d=8,
                feed_tie='origin', feed_tmax=None):
    """Complacency with a different grab split direction.

    count: None (fixed order), or a key of COUNTS: pick the empty neighbour with the most empty squares counted.
    tie: 'origin' (ties: most away from the stored origin, then FIXED) or 'fixed' (ties: FIXED).
    away_first: pick the empty neighbour most away from the origin first (count, if any, breaks its ties).
    alt: None, or 'parity': order (DOWN, RIGHT, UP, LEFT) on even x + y, (UP, LEFT, DOWN, RIGHT) on odd.
    gate1: False keeps Complacency's fixed order on its e >= 16 gate-1 split (the asm would leave that path alone).
    feed: None, 'boxed' (no empty neighbour, e >= feed_d: feed a friend neighbour that has an empty neighbour,
          preferring away from the origin) or 'outward' (no empty square in the 5x5, e >= feed_d: feed the friend
          neighbour most away from the origin, if that is > 0).
    feed_tie: which candidate a 'boxed' feed picks: 'origin' (most away from the origin, then FIXED), 'fixed'
          (first of UP, RIGHT, DOWN, LEFT, no memory) or 'poorest' (lowest energy, then UP, RIGHT, DOWN, LEFT).
    feed_tmax: None, or only feed a friend with energy <= feed_tmax (Contagion's grab assist uses 4).
    """
    base = cells_ref.complacency
    sq = COUNTS[count] if count else None

    def pol(view, mem):
        org = _origin(view, mem)
        act, n, t = base(view, mem)
        c = view.cells
        if any(c[i] == CELL_ENEMY for i in range(25)):
            return act, n, t                       # not the grab: Complacency as it is
        kind = act & 0xF0
        if kind == ACT_SPLIT:
            if not gate1 and view.energy >= cells_ref.SCOURGE_THREAT_MIN:
                return act, n, t
            empty = [d for d in FIXED if c[NB[d]] == CELL_EMPTY]
            if alt == 'parity' and (view.x + view.y) & 1:
                order = (UP, LEFT, DOWN, RIGHT)
            else:
                order = FIXED

            def key(d):
                k = []
                if away_first:
                    k.append(-_away(view, org, d))
                if sq:
                    k.append(-sum(1 for i in sq[d] if c[i] == CELL_EMPTY))
                if tie == 'origin' and not away_first:
                    k.append(-_away(view, org, d))
                k.append(order.index(d))
                return k
            return ACT_SPLIT + min(empty, key=key), n, t
        if feed and view.energy >= feed_d and (act == ACT_REST or kind == ACT_FEED):
            if feed == 'boxed':
                if any(c[NB[d]] == CELL_EMPTY for d in FIXED):
                    return act, n, t
                cand = [d for d in FIXED if c[NB[d]] == CELL_FRIEND and
                        any(c[i] == CELL_EMPTY for i in _ring4(d)) and
                        (feed_tmax is None or view.energies[NB[d]] <= feed_tmax)]
                if cand and feed_tie == 'fixed':
                    return ACT_FEED + min(cand, key=FEED_ORDER.index), n, t
                if cand and feed_tie == 'poorest':
                    return ACT_FEED + min(cand, key=lambda d: (view.energies[NB[d]], FEED_ORDER.index(d))), n, t
            else:
                if any(c[i] == CELL_EMPTY for i in range(25)):
                    return act, n, t
                cand = [d for d in FIXED if c[NB[d]] == CELL_FRIEND and _away(view, org, d) > 0]
            if cand:
                d = min(cand, key=lambda d: (-_away(view, org, d), FIXED.index(d)))
                return ACT_FEED + d, n, t
        return act, n, t
    return pol


POLICIES = {
    'a': ('Complacency as it is', None),
    'b': ('most empties in the neighbour 3x3; tie origin', dict(count='b')),
    'c': ('most empties among the neighbour 4; tie origin', dict(count='c')),
    'c-fixed': ('(c), ties fixed order (no memory)', dict(count='c', tie='fixed')),
    'w-fixed': ('(c) on window 6..21 (no 2/22), ties fixed order', dict(count='w', tie='fixed')),
    'c-g1': ('(c), but the e >= 16 gate-1 split keeps the fixed order', dict(count='c', gate1=False)),
    'd6': ('(b) + boxed outward feeding D=6', dict(count='b', feed='boxed', feed_d=6)),
    'd8': ('(b) + boxed outward feeding D=8', dict(count='b', feed='boxed', feed_d=8)),
    'd6o': ('(b) + no-empty-in-5x5 outward feeding D=6', dict(count='b', feed='outward', feed_d=6)),
    'd8o': ('(b) + no-empty-in-5x5 outward feeding D=8', dict(count='b', feed='outward', feed_d=8)),
    'a+f6': ('fixed split order + boxed feeding D=6', dict(feed='boxed', feed_d=6)),
    'a+f6x': ('fixed split order + boxed feeding D=6, feed ties U,R,D,L (no memory)',
              dict(feed='boxed', feed_d=6, feed_tie='fixed')),
    'w+f6': ('w-fixed + boxed feeding D=6', dict(count='w', tie='fixed', feed='boxed', feed_d=6)),
    'w+f6x': ('w-fixed + boxed feeding D=6, feed ties U,R,D,L (no memory)',
              dict(count='w', tie='fixed', feed='boxed', feed_d=6, feed_tie='fixed')),
    'w+f5x': ('w+f6x with D=5', dict(count='w', tie='fixed', feed='boxed', feed_d=5, feed_tie='fixed')),
    'w+f7x': ('w+f6x with D=7', dict(count='w', tie='fixed', feed='boxed', feed_d=7, feed_tie='fixed')),
    'w+f6p': ('w-fixed + boxed feeding D=6 to the poorest candidate',
              dict(count='w', tie='fixed', feed='boxed', feed_d=6, feed_tie='poorest')),
    'w+f6x4': ('w+f6x, only to a friend with e <= 4 (Contagion-style)',
               dict(count='w', tie='fixed', feed='boxed', feed_d=6, feed_tie='fixed', feed_tmax=4)),
    'b+f5': ('(b) + boxed feeding D=5', dict(count='b', feed='boxed', feed_d=5)),
    'h': ('most empties in the view half on that side; tie origin', dict(count='h')),
    'away': ('most away from the origin; tie fixed order', dict(away_first=True)),
    'away-c': ('most away from the origin; tie (c) count', dict(away_first=True, count='c')),
    'parity': ('fixed order flipped on odd x + y', dict(alt='parity')),
    'parity-c': ('(c), ties by the parity order', dict(count='c', tie='fixed', alt='parity')),
}

MILESTONES = (128, 512)
SNAPS = (25, 50, 100, 200)


def get_policy(name):
    kw = POLICIES[name][1]
    return cells_ref.complacency if kw is None else make_policy(**kw)


def starts(n, seed, w=64, h=64):
    rng = random.Random(seed)
    return [(rng.randrange(w), rng.randrange(h)) for _ in range(n)]


def run_one(policy, start, ticks, seed=0):
    eng = E.Engine([policy], seed=seed, max_ticks=ticks, start_mode='fixed', start_positions=[start])
    first = {m: None for m in MILESTONES}
    snaps = {}
    while eng.step():
        p = eng.pop[0]
        for m in MILESTONES:
            if first[m] is None and p >= m:
                first[m] = eng.tick
        if eng.tick in SNAPS:
            snaps[eng.tick] = p
    p = eng.pop[0]
    for m in MILESTONES:
        if first[m] is None and p >= m:
            first[m] = eng.tick
    if eng.tick in SNAPS:
        snaps[eng.tick] = p
    return first, snaps


def quart(xs):
    """(q1, median, q3) by the nearest-rank-free linear method; None values (never reached) sort last."""
    big = 10 ** 9
    v = sorted(big if x is None else x for x in xs)
    if not v:
        return None

    def q(f):
        k = (len(v) - 1) * f
        lo = int(k)
        hi = min(lo + 1, len(v) - 1)
        if v[hi] >= big and k > lo or v[lo] >= big:
            return None
        return v[lo] + (v[hi] - v[lo]) * (k - lo)
    return q(0.25), q(0.5), q(0.75)


def fmt(t):
    if t is None:
        return '-'
    q1, m, q3 = t
    f = lambda x: '-' if x is None else ('%g' % round(x, 1))  # noqa: E731
    return '%s (%s-%s)' % (f(m), f(q1), f(q3))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--policies', default=','.join(POLICIES))
    ap.add_argument('--starts', type=int, default=50)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--ticks', type=int, default=200)
    args = ap.parse_args(argv)
    try:
        import experiments as X
        X.lower_priority()
    except Exception:
        pass
    pts = starts(args.starts, args.seed)
    edge = sorted(min(x, y, 63 - x, 63 - y) for x, y in pts)
    print('starts: %d (seed %d), nearest-edge distance median %g, min %d, max %d' % (
        len(pts), args.seed, quart(edge)[1], edge[0], edge[-1]))
    print('| Policy | 128 at | 512 at | t25 | t50 | t100 | t200 | s |')
    print('|---|---|---|---|---|---|---|---|')
    for name in args.policies.split(','):
        t0 = time.time()
        rows = [run_one(get_policy(name), s, args.ticks, seed=k) for k, s in enumerate(pts)]
        cols = [fmt(quart([r[0][m] for r in rows])) for m in MILESTONES]
        cols += [fmt(quart([r[1].get(s) for r in rows])) for s in SNAPS if s <= args.ticks]
        print('| %s: %s | %s | %.0f |' % (name, POLICIES[name][0], ' | '.join(cols), time.time() - t0))
        sys.stdout.flush()


if __name__ == '__main__':
    main()
