"""Scratch (review addition 2): far anatomy.  Far open cells with energy >= 5 that had no event ('none'), by energy
bucket: 5-11 (Bane v2.2: rule 4, 39-66 instructions), 12-15 (rule 4: no refill pattern without an enemy, threshold 16),
16+ (gate split, 16).  Real games from budget.csv (Bane vs the rival, given games, windows a / b / c), then the same
share in solo runs of Bane v2.2 from the same start squares (solo engine, seed 3; 'none' = position unchanged and
energy not lower after the tick, so no split, move or feed; every solo cell is far).
Usage: python far_none.py <repo root> <budget.csv> > out.txt
"""
import collections
import csv
import os
import sys

ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'sim'))
GROUPS = (('VarSi', ('129850', '131102', '131312', '129308', '130482', '130818', '131265', '131276', '131114',
                     '130915', '130988')),
          ('Colossus', ('129876', '130711', '131125', '129859', '129907')))
EB = {'5-11': '5-11', '12-15': '12-15', '16-49': '16+', '50': '16+'}
WS = 'abc'


def real():
    c = collections.Counter()
    for r in csv.DictReader(open(sys.argv[2], encoding='utf-8')):
        if r['window'] not in WS or r['space'] != 'open' or r['enemy'] != 'far' or r['energy'] not in EB:
            continue
        for riv, games in GROUPS:
            if r['replay'] not in games:
                continue
            who = 'Bane' if r['name'].startswith('Bane') else riv if riv in r['name'] else None
            if who is None or r['act'] == 'unknown':
                continue
            k = (riv, who, r['window'], EB[r['energy']])
            c[k + ('n',)] += int(r['n'])
            c[k + (r['act'],)] += int(r['n'])
    print('REAL: far open e>=5, share with no event (none %) and split %, by energy | n')
    for riv, _ in GROUPS:
        for who in ('Bane', riv):
            for w in WS:
                print('%-8s games %-8s %s |' % (riv, who, w), ' | '.join(
                    '%-5s none %5.1f split %5.1f n %6d' % (b, 100.0 * c[(riv, who, w, b, 'none')] / max(c[(riv, who, w, b, 'n')], 1),
                                                            100.0 * c[(riv, who, w, b, 'split')] / max(c[(riv, who, w, b, 'n')], 1),
                                                            c[(riv, who, w, b, 'n')]) for b in ('5-11', '12-15', '16+')))


def solo_one(start):
    import engine as E
    import cells_ref
    eng = E.Engine([cells_ref.bane2], seed=3, max_ticks=100, start_mode='fixed', start_positions=[start])
    c = collections.Counter()
    while True:
        t = eng.tick
        w = 'a' if t < 30 else 'b' if t < 60 else 'c'
        before = {}
        for i, alive in enumerate(eng.c_alive):
            if not alive:
                continue
            q, e = eng.c_pos[i], eng.c_en[i]
            if e < 5 or not any(eng.grid[q + d] == E.GRID_EMPTY for d in eng.dirs):
                continue
            before[i] = (q, e, '5-11' if e < 12 else '12-15' if e < 16 else '16+')
        if not eng.step():
            break
        for i, (q, e, b) in before.items():
            moved = not eng.c_alive[i] or eng.c_pos[i] != q or eng.c_en[i] < e
            c[(w, b, 'n')] += 1
            c[(w, b, 'none')] += not moved
    return c


if __name__ == '__main__':
    real()
    sys.argv = [sys.argv[0], ROOT, os.path.join(ROOT, 'data', 'evidence-2026-11-12', 'scripts', 'x.txt')]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import solo_starts as SS
    tot = collections.Counter()
    for grp, specs in SS.GAMES.items():
        for spec in specs:
            for k, v in solo_one(SS.start_of(spec)).items():
                tot[k] += v
    print('\nSOLO Bane v2.2 from the same 11 start squares (pooled): far open e>=5, no-event share by energy | n')
    for w in WS:
        print('solo %s |' % w, ' | '.join('%-5s none %5.1f n %6d' % (b, 100.0 * tot[(w, b, 'none')] / max(tot[(w, b, 'n')], 1),
                                                                 tot[(w, b, 'n')]) for b in ('5-11', '12-15', '16+')))
