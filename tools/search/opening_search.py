"""Solo opening search (scratch; no simulator or cell changes).  One colony alone on the board, real engine.
Usage: python opening_search.py <repo root> <set name>
Prints the mean cell count over the start squares at several ticks for each rule set.
"""
import sys
import os
import itertools
from multiprocessing import Pool

ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'sim'))
import engine as E  # noqa: E402
import cells_ref  # noqa: E402

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
IDX = (7, 13, 17, 11)
BEYOND = (2, 14, 22, 10)
# the 5 view squares on each side beyond the neighbour (the outer ring part that faces direction d)
SIDE = {UP: (0, 1, 2, 3, 4, 6, 8), RIGHT: (4, 9, 14, 19, 24, 8, 18), DOWN: (20, 21, 22, 23, 24, 16, 18),
        LEFT: (0, 5, 10, 15, 20, 6, 16)}
RING = {UP: (6, 8, 2), RIGHT: (8, 14, 18), DOWN: (16, 18, 22), LEFT: (6, 10, 16)}
STARTS = ((30, 31), (8, 9), (2, 60), (30, 3))
TICKS = (20, 30, 40, 50, 60, 75, 100)
MOVE, SPLIT, FEED, REST = 0x10, 0x20, 0x40, 0x01


def make(kl=8, ks=2, long_rule='first', dir_rule='rot', stop='steps', smin=2, extend=0, feed=6, feed_any=False,
         kl2=None, t2=0, split_min=5, long_e=0, wait=False, fat_k=None):
    """Memory: [0] bearing, [1] steps left, [2] steps taken, [4..7] position of the last split."""
    def pol(view, mem):
        c, e = view.cells, view.energy
        pos = (view.x | view.y << 16).to_bytes(4, 'little')
        here = bytes(mem[4:8]) == pos
        empty = [d for d in range(4) if c[IDX[d]] == 0]
        friends = sum(1 for i in range(25) if i != 12 and c[i] == 1)
        if not empty:
            if feed and e >= feed:
                for d in range(4):
                    if c[IDX[d]] == 1 and (feed_any or any(c[i] == 0 for i in RING[d])):
                        return FEED + d, 30, 30
            return REST, 30, 30
        if mem[1] and not here:                          # walker
            b = mem[0] & 3
            if c[IDX[b]] == 0 and not (stop == 'sparse' and mem[2] >= smin and friends == 0):
                mem[1] -= 1
                mem[2] += 1
                return MOVE + b, 30, 30
            mem[1] = 0
        elif extend and not here and mem[2] < extend + 16 and mem[2] and friends >= extend_min[0] \
                and c[IDX[mem[0] & 3]] == 0 and e < split_min:
            mem[2] += 1                                   # crowded where it stopped: walk on
            return MOVE + (mem[0] & 3), 30, 30
        if e < split_min:
            return REST, 30, 30
        b = mem[0] & 3
        first = not here
        order = [(b + k) & 3 for k in range(4)] if first else [(b + 1 + k) & 3 for k in range(4)]
        if dir_rule == 'open':                           # the emptiest side first, ties in rotation order
            order.sort(key=lambda d: sum(1 for i in SIDE[d] if c[i] == 1) + (0 if c[BEYOND[d]] == 0 else 1))
        d = next(x for x in order if c[IDX[x]] == 0)
        klong = kl2 if (kl2 is not None and view.tick >= t2) else kl
        if long_rule == 'first':
            far = first and d == b
        elif long_rule == 'open':
            far = c[BEYOND[d]] == 0 and not any(c[i] == 1 for i in SIDE[d])
        elif long_rule == 'all':
            far = True
        else:
            far = False
        if far and e < long_e:
            if wait and first and c[BEYOND[d]] == 0:
                return REST, 30, 30                       # fatten first, then send a walker that can split on arrival
            far = False
        if fat_k is not None and e >= 10:
            far, klong = True, fat_k                      # a child with 5 or more: always a long walker
        mem[0], mem[1], mem[2] = d, (klong if far else ks), 0
        mem[4:8] = pos
        return SPLIT + d, 30, 30
    extend_min = [extend]
    return pol


def run(args):
    name, kw, start = args
    pol = cells_ref.bane2 if kw is None else make(**kw)
    eng = E.Engine([pol], seed=3, max_ticks=100, start_mode='fixed', start_positions=[start])
    pops = {}
    while eng.step():
        pops[eng.tick] = eng.pop[0]
    pops[eng.tick] = eng.pop[0]
    return name, [pops.get(t, 0) for t in TICKS]


SETS_B = [('first 8/2 dir-open (base)', dict(dir_rule='open')),
          ('split at 6', dict(dir_rule='open', split_min=6)),
          ('split at 8', dict(dir_rule='open', split_min=8)),
          ('split at 10', dict(dir_rule='open', split_min=10)),
          ('long only from 10, else short', dict(dir_rule='open', long_e=10)),
          ('long from 10, wait for it', dict(dir_rule='open', long_e=10, wait=True)),
          ('long from 8, wait for it', dict(dir_rule='open', long_e=8, wait=True)),
          ('open-long 6, from 10, wait', dict(dir_rule='open', long_rule='open', kl=6, long_e=10, wait=True)),
          ('open-long 12, from 10, wait', dict(dir_rule='open', long_rule='open', kl=12, long_e=10, wait=True)),
          ('first 16, from 10, wait', dict(dir_rule='open', kl=16, long_e=10, wait=True)),
          ('base + fat children walk 8', dict(dir_rule='open', fat_k=8)),
          ('split at 10, all long 8', dict(dir_rule='open', split_min=10, long_rule='all', kl=8)),
          ('split at 10, all long 4', dict(dir_rule='open', split_min=10, long_rule='all', kl=4)),
          ('split at 10, open-long 8/1', dict(dir_rule='open', split_min=10, long_rule='open', kl=8, ks=1)),
          ]
SETS = {
    'a': [('bane v2.2 (real cell)', None),
          ('first 8/2 (same rule, sketch)', dict()),
          ('open-long 8/2', dict(long_rule='open')),
          ('open-long 8/2 dir-open', dict(long_rule='open', dir_rule='open')),
          ('first 8/2 dir-open', dict(dir_rule='open')),
          ('open-long 6/2 dir-open', dict(long_rule='open', dir_rule='open', kl=6)),
          ('open-long 12/2 dir-open', dict(long_rule='open', dir_rule='open', kl=12)),
          ('open-long 8/1 dir-open', dict(long_rule='open', dir_rule='open', ks=1)),
          ('open-long 8/3 dir-open', dict(long_rule='open', dir_rule='open', ks=3)),
          ('all-long 4', dict(long_rule='all', kl=4)),
          ('all-long 3 dir-open', dict(long_rule='all', kl=3, dir_rule='open')),
          ('open-long 8/2 sparse-stop 2', dict(long_rule='open', dir_rule='open', stop='sparse', smin=2)),
          ('open-long 8/2 sparse-stop 3', dict(long_rule='open', dir_rule='open', stop='sparse', smin=3)),
          ('open-long 16/2 sparse-stop 3', dict(long_rule='open', dir_rule='open', kl=16, stop='sparse', smin=3)),
          ('open-long 16/2 sparse-stop 4', dict(long_rule='open', dir_rule='open', kl=16, stop='sparse', smin=4)),
          ('first 8/2 no feed', dict(feed=0)),
          ('first 8/2 feed any', dict(feed_any=True)),
          ('none 0/1 (no long walks)', dict(long_rule='none', ks=1)),
          ('none 0/0 (no walking)', dict(long_rule='none', ks=0)),
          ],
}

if __name__ == '__main__':
    SETS['b'] = SETS_B
    sets = SETS[sys.argv[2]]
    jobs = [(n, kw, st) for n, kw in sets for st in STARTS]
    try:
        import experiments
        experiments.lower_priority()
    except Exception:
        pass
    with Pool(4) as p:
        res = p.map(run, jobs)
    print('%-34s' % 'rule set (mean of 4 starts)' + ''.join('%7d' % t for t in TICKS))
    for n, _ in sets:
        rows = [r for nm, r in res if nm == n]
        print('%-34s' % n + ''.join('%7d' % (sum(r[i] for r in rows) // len(rows)) for i in range(len(TICKS))))
