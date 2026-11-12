"""Scratch: races of our Bane v2.1/v2.2 cells (race.csv) and first-order race flips for other bite layouts.
Usage: python race_sum.py <out.txt> <race.csv>

Part 1, per rival and window (a = t < 100, b = t >= 100): races our cell won ('A': it bit its planned target before
anything bit it) and lost ('B': an enemy bit it first, it was stunned), by our plan: lock (stored bite, 4) or first
(bite_tbl scan, 16); lost races also by the enemy's measured cost class.

Part 2, first-order flips per layout (our cost for a lock situation / a first-bite situation):
  v2.2 (4 / 16) | v2.3a (4 / 11) | v2.3b (4 / 10) | scan-first (5 / 5) | queue3 (3 / 16) | queue3+11 (3 / 11)
  gained = lost races whose enemy bite cost more than our new cost (ties: half).  lost = won races (plan lock) in which
  the enemy was armed on our cell (it bit our cell on the previous tick) and its usual cost for that direction is below
  our new cost (ties: half): a lower bound (an unarmed enemy may also have meant to bite).  Enemy costs: the measured
  class of that bite for lost races; for won races the usual cost by rival and direction (section 12): Siect-F 3; VarSi,
  CogSpore, CogBloomXT, Clippy UP/DOWN 4, LEFT/RIGHT 5-15; Colossus, medivac, NomNom2 5; others unknown (left out).
  The 5-15 class is shown as two bounds: [all at 5 .. all at 15].  'other' (no marker on one side) is left out.
  This counts races only.  It does not replay the game after a flipped race.
"""
import collections
import csv
import sys

NORM = {'CogSpore - VarSi': 'VarSi', 'CogSpore-Siect-F': 'Siect-F', 'CogBloomXT v4': 'CogBloomXT',
        'Clippy-Var:Si-Gt:Fr': 'Clippy'}
FIVE = {'Colossus', 'medivac', 'NomNom2'}
YEN = {'VarSi', 'CogSpore', 'CogBloomXT', 'Clippy'}
LAYOUTS = (('v2.2', 4, 16), ('v2.3a', 4, 11), ('v2.3b', 4, 10), ('scan-first', 5, 5), ('queue3', 3, 16),
           ('queue3+11', 3, 11))


def cost_set(rv, c):
    """Possible enemy costs for a measured class (lost race)."""
    if c == '<4':
        return (3, 3)
    if c == '=4':
        return (4, 4)
    if c == '5-15':
        return (5, 5) if rv in FIVE else (5, 15)
    if c == '=16':
        return (16, 16)
    if c == '>16':
        return (17, 17)
    return None


def usual(rv, d):
    if rv == 'Siect-F':
        return (3, 3)
    if rv in YEN:
        return (4, 4) if d in 'UD' else (5, 15)
    if rv in FIVE:
        return (5, 5)
    return None


def win_share(ours, theirs):
    return 1.0 if ours < theirs else 0.5 if ours == theirs else 0.0


rows = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
R = collections.defaultdict(collections.Counter)
G = collections.defaultdict(set)
for r in rows:
    if r['rival'] == '_check':
        continue
    rv = NORM.get(r['rival'], r['rival'])
    R[rv][(r['window'], r['first'], r['plan'], r['bcost'], r['rdir'], r['a_armed'], r['b_armed'])] += int(r['n'])
    G[rv].add(r['replay'])
out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P(__doc__)
order = sorted(R, key=lambda v: -sum(R[v].values()))
P('## Part 1: races (thousands of cell-ticks; % of row)')
P('%-12s %-3s %9s | %-34s | %-60s' % ('rival', 'w', 'races', 'won: lock / first', 'lost: lock (<4 =4 5-15 oth) / first (<4 =4 5-15 oth) / plan-other'))
for rv in order:
    if len(G[rv]) < 2:
        continue
    for w in ('a', 'b'):
        c = {k: v for k, v in R[rv].items() if k[0] == w}
        tot = sum(c.values())
        if tot < 200:
            continue
        g = lambda f: sum(v for k, v in c.items() if f(k))
        wl, wf = g(lambda k: k[1] == 'A' and k[2] == 'lock'), g(lambda k: k[1] == 'A' and k[2] == 'first')
        cl = [g(lambda k, x=x: k[1] == 'B' and k[2] == 'lock' and (k[3] == x if x != 'oth' else k[3] not in ('<4', '=4', '5-15')))
              for x in ('<4', '=4', '5-15', 'oth')]
        cf = [g(lambda k, x=x: k[1] == 'B' and k[2] == 'first' and (k[3] == x if x != 'oth' else k[3] not in ('<4', '=4', '5-15')))
              for x in ('<4', '=4', '5-15', 'oth')]
        co = g(lambda k: k[1] == 'B' and k[2].endswith('-other'))
        pc = lambda x: 100 * x / tot
        P('%-12s %-3s %9d | %5.1f / %5.1f                      | %4.1f %4.1f %4.1f %4.1f / %4.1f %4.1f %4.1f %4.1f / %4.1f'
          '   (%d games)' % (rv, w, tot, pc(wl), pc(wf), *map(pc, cl), *map(pc, cf), pc(co), len(G[rv])))

P('\n## Part 2: first-order race flips per layout, as % of all races with that rival in that window')
P('(gained - lost; [low .. high] where the 5-15 class matters)')
P('%-12s %-3s %9s | %s' % ('rival', 'w', 'races', ' | '.join('%-22s' % l[0] for l in LAYOUTS)))
for rv in order:
    if len(G[rv]) < 2:
        continue
    for w in ('a', 'b'):
        c = {k: v for k, v in R[rv].items() if k[0] == w}
        tot = sum(c.values())
        if tot < 200:
            continue
        cells = []
        for name, cl, cfst in LAYOUTS:
            lo_net = hi_net = 0.0
            known = True
            for (ww, fi, plan, bc, rd, aa, ba), n in c.items():
                if fi == 'B' and plan in ('lock', 'first'):
                    cs = cost_set(rv, bc)
                    if cs is None:
                        continue
                    ours = cl if plan == 'lock' else cfst
                    base = 4 if plan == 'lock' else 16
                    g0 = [win_share(ours, x) - win_share(base, x) for x in cs]
                    lo_net += n * min(g0)
                    hi_net += n * max(g0)
                elif fi == 'A' and plan == 'lock' and ba == '1':
                    us = usual(rv, rd)
                    if us is None:
                        continue
                    g0 = [win_share(cl, x) - win_share(4, x) for x in us]
                    lo_net += n * min(g0)
                    hi_net += n * max(g0)
            if abs(lo_net - hi_net) < 1e-9:
                cells.append('%+6.2f%%' % (100 * lo_net / tot))
            else:
                cells.append('[%+6.2f .. %+6.2f]' % (100 * lo_net / tot, 100 * hi_net / tot))
        P('%-12s %-3s %9d | %s' % (rv, w, tot, ' | '.join('%-22s' % x for x in cells)))
out.close()
