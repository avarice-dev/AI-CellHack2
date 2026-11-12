"""Scratch: blind-queue sizing rules scored on our real bite chains (queue.csv).  Usage: python queue_sum.py <out> <csv>
A queue armed at a chain start with k blind bites (3 instructions each, the view not read) hits T min(k, H) times and
bites an empty or refilled square max(0, k - H) times; the H - k later ticks T is still there are left to the checked
path.  Rules (e0 = T's energy at the chain start as our cell sees it, nf = our other cells next to T):
  conviction: k = clamp(ceil((e0 - 2) / 2), 3, 7)        (Conviction's queue: an unfed target's need, at least 3)
  need:       k = clamp(ceil((e0 - 2) / 2), 0, 7)        (same without the minimum)
  shared:     k = clamp(ceil((e0 - 2(1 + nf)) / (2(1 + nf))), 0, 7)   (every visible attacker bites T each tick)
  shared-1:   shared minus one (a margin)
  one:        k = 1 if shared >= 1 else 0
Per rival and window: chains, mean H, share dying within the horizon; per rule: blind bites per chain, empty-square
share of blind bites (wasted turns), coverage = hits / sum of H (share of T's remaining ticks bitten at 3).
First-order: T's survival is the real one under v2.2's bites; a 3-instruction queue would change the races after.
"""
import collections
import csv
import math
import sys

NORM = {'CogSpore - VarSi': 'VarSi', 'CogSpore-Siect-F': 'Siect-F', 'CogBloomXT v4': 'CogBloomXT',
        'Clippy-Var:Si-Gt:Fr': 'Clippy'}


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def shared(e0, nf):
    a = 2 * (1 + nf)
    return clamp(math.ceil((e0 - a) / a), 0, 7)


RULES = (('conviction', lambda e, nf: clamp(math.ceil((e - 2) / 2), 3, 7)),
         ('need', lambda e, nf: clamp(math.ceil((e - 2) / 2), 0, 7)),
         ('shared', shared),
         ('shared-1', lambda e, nf: max(0, shared(e, nf) - 1)),
         ('one', lambda e, nf: 1 if shared(e, nf) >= 1 else 0))
rows = [r for r in csv.DictReader(open(sys.argv[2], encoding='utf-8')) if r['rival'] != '_check']
C = collections.defaultdict(list)
G = collections.defaultdict(set)
for r in rows:
    rv = NORM.get(r['rival'], r['rival'])
    for w in (r['window'], 'all'):
        C[(rv, w)].append((int(r['e0']), int(r['nf']), int(r['ntf']), int(r['H']), r['end'], int(r['n'])))
        C[('ALL', w)].append((int(r['e0']), int(r['nf']), int(r['ntf']), int(r['H']), r['end'], int(r['n'])))
    G[rv].add(r['replay'])
    G['ALL'].add(r['replay'])
out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P(__doc__)
P('%-12s %-3s %8s %5s %5s | %s' % ('rival', 'w', 'chains', 'H', 'died', ' | '.join('%-24s' % (n + ': k / empty / cover')
                                                                                 for n, _ in RULES)))
order = sorted({k[0] for k in C}, key=lambda v: -sum(x[-1] for x in C[(v, 'all')]))
for rv in order:
    if len(G[rv]) < 2:
        continue
    for w in ('a', 'b', 'all'):
        L = C.get((rv, w))
        if not L:
            continue
        n = sum(x[-1] for x in L)
        if n < 200:
            continue
        Hs = sum(x[3] * x[-1] for x in L)
        died = sum(x[-1] for x in L if x[4] == 'died')
        cells = []
        for name, f in RULES:
            q = hits = miss = 0
            for e0, nf, ntf, H, end, m in L:
                k = f(e0, nf)
                q += k * m
                hits += min(k, H) * m
                miss += max(0, k - H) * m
            cells.append('%4.2f / %5.1f%% / %5.1f%%' % (q / n, 100 * miss / q if q else 0, 100 * hits / Hs if Hs else 0))
        P('%-12s %-3s %8d %5.2f %4.0f%% | %s' % (rv, w, n, Hs / n, 100 * died / n, ' | '.join('%-24s' % c for c in cells)))
out.close()
