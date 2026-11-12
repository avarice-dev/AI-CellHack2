"""Scratch: Bane v2.2 ALONE on the board from each given start square (real engine, no rival models).
The solo curve from a colony's own start square is what its start position allows; real / solo = what the game
(rivals, contact) took away.  Bane v2.x, Conviction and Penalty share this opening, so one curve serves all three.
Usage: python solo_baseline.py <repo root> <starts.txt: one 'x y' per line> <out.csv> [procs]
"""
import csv
import os
import sys
from multiprocessing import Pool

ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'sim'))
import engine as E  # noqa: E402
import cells_ref  # noqa: E402

TICKS = (20, 30, 40, 50, 60, 80, 100)


def run(start):
    eng = E.Engine([cells_ref.bane2], seed=3, max_ticks=max(TICKS), start_mode='fixed', start_positions=[start])
    pops = {}
    while eng.step():
        pops[eng.tick] = eng.pop[0]
    pops[eng.tick] = eng.pop[0]
    return start, [pops.get(t, pops[max(pops)]) for t in TICKS]


if __name__ == '__main__':
    starts = sorted({tuple(int(v) for v in line.split()) for line in open(sys.argv[2]) if line.strip()})
    with Pool(int(sys.argv[4]) if len(sys.argv) > 4 else 2) as p:
        res = p.map(run, starts)
    with open(sys.argv[3], 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['x', 'y'] + ['s%d' % t for t in TICKS])
        for (x, y), pops in res:
            w.writerow([x, y] + pops)
    print('wrote %d starts' % len(res))
