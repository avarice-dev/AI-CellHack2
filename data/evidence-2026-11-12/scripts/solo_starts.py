"""Scratch (review point; solo engine only, no rival models): is the 'bad start' our own opening?
For each sampled game, Bane's real start square (first frame of the replay) is replayed with Bane v2.2 ALONE and
with the best opening-search variant ('open-long 6/2 dir-open', tools/search/opening_search.py) alone.
Per run: cells at t30 / t60, and the boxed share in window a (t < 30): cell-ticks with no empty edge neighbour
(walls and own cells count as not empty) / all cell-ticks.  Real window-a boxed shares are in m2-varsi-budget.txt.
Usage: python solo_starts.py <repo root> <out.txt> [procs]
"""
import collections
import gzip
import json
import os
import struct
import sys
from multiprocessing import Pool

ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'sim'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'search'))
GAMES = collections.OrderedDict([
    ('bad', ('pull9/131114', 'pull9/130915', 'pull9/130988')),
    ('equal', ('pull7/129308', 'pull9/130482', 'pull9/130818', 'pull9/131265', 'pull9/131276')),
    ('good', ('pull8/129850', 'pull9/131102', 'pull9/131312'))])


def start_of(spec):
    pull, rid = spec.split('/')
    names = json.load(open(os.path.join(ROOT, 'data', pull, 'names.json'), encoding='utf-8'))[rid]
    col = [i for i, n in enumerate(names) if 'Bane' in n][0]
    raw = gzip.decompress(open(os.path.join(ROOT, 'data', pull, 'replays', rid + '.chr2.gz'), 'rb').read())
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    BIRTH = struct.Struct('<IBHHB')
    while True:
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = struct.unpack_from('<II', raw, p); p += 8
            for i in range(n):
                cid, c, x, y, e = BIRTH.unpack_from(raw, p + 10 * i)
                if c == col:
                    return (x, y)
            raise ValueError('no Bane cell in the first frame of %s' % rid)
        raise ValueError('first record is not a frame in %s' % rid)


def run(args):
    import engine as E
    import cells_ref
    which, start = args
    if which == 'v2.2':
        pol = cells_ref.bane2
    else:
        sys.argv = [sys.argv[0], ROOT]                # opening_search reads ROOT from argv at import
        import opening_search as OS
        pol = OS.make(long_rule='open', dir_rule='open', kl=6)
    eng = E.Engine([pol], seed=3, max_ticks=60, start_mode='fixed', start_positions=[start])
    pops, boxed, ticks = {}, 0, 0
    while True:
        if eng.tick < 30:
            for i, alive in enumerate(eng.c_alive):
                if not alive:
                    continue
                q = eng.c_pos[i]
                ticks += 1
                boxed += all(eng.grid[q + d] != E.GRID_EMPTY for d in eng.dirs)
        if not eng.step():
            break
        pops[eng.tick] = eng.pop[0]
    pops[eng.tick] = eng.pop[0]
    return which, start, pops.get(30, 0), pops.get(60, pops[max(pops)]), 100.0 * boxed / max(ticks, 1)


if __name__ == '__main__':
    starts = {spec: start_of(spec) for grp in GAMES.values() for spec in grp}
    jobs = [(w, s) for w in ('v2.2', 'open-long 6/2') for s in sorted(set(starts.values()))]
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 2) as pool:
        res = {(w, s): r for w, s, *r in pool.map(run, jobs)}
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write('Solo from Bane\'s real start square: cells t30 / t60, window-a boxed %% (v2.2 | open-long 6/2 dir-open)\n')
        for grp, specs in GAMES.items():
            agg = collections.Counter()
            for spec in specs:
                s = starts[spec]
                a, b = res[('v2.2', s)], res[('open-long 6/2', s)]
                f.write('%-5s %-12s start %-8s | v2.2 %4d / %5d boxed %5.1f%% | 6/2 %4d / %5d boxed %5.1f%%\n' % (
                    grp, spec, '%d,%d' % s, a[0], a[1], a[2], b[0], b[1], b[2]))
                for k, v in zip(('a30', 'a60', 'abox', 'b30', 'b60', 'bbox'), a + b):
                    agg[k] += v
            n = len(specs)
            f.write('%-5s mean%s | v2.2 %4.0f / %5.0f boxed %5.1f%% | 6/2 %4.0f / %5.0f boxed %5.1f%%\n\n' % (
                grp, ' ' * 17, *(agg[k] / n for k in ('a30', 'a60', 'abox', 'b30', 'b60', 'bbox'))))
    print(open(sys.argv[2], encoding='utf-8').read())
