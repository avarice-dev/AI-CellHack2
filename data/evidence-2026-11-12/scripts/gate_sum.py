"""Scratch: summary of gate_split.csv (measure B1).  Usage: python gate_sum.py <gate_split.csv> > out.txt
Tables: lost-square shares by rule, hold detail, lost episodes, fills (with the square held after 10 and the
enemies beside s), and the hold delay view (hct / hep rows, review point).
Rule labels (Bane v2.2 rules, games with id >= 127810 only; rivals are shown raw): for our best neighbour c of a
contested square s with no event this tick, thr = 12 if c has a refill-pattern edge (FREED_BY) else 16:
  thin        e < 5
  hold        5 <= e < thr and an enemy on c's diagonal (the prey hold = the gate waiting)
  rule4-1     5 <= e < thr, no diagonal enemy, s is c's only empty edge: rule 4's split / move into s lost the race
  rule4-n     the same with 2+ empty edges (target unknown: may have gone elsewhere and failed, or walked)
  gate-s      e >= thr and s is the gate's target: the gate split into s lost the race
  gate-other  e >= thr, target another square (that split failed: occupied first)
Other events as logged (split = split elsewhere succeeded; unknown = split parent not identified, kept out).
Windows: a t < 30, b < 60, c < 100, d later.  Equal-start VarSi losses (pack s4): 129308 130482 130818 131265 131276.
"""
import collections
import csv
import sys

EQ = ('129308', '130482', '130818', '131265', '131276')
WS = 'abcd'


def label(f):
    res, ev, e, d, side, beyond, cdiag, fr, first, ne = f[:10]
    e, cdiag, fr, first, ne = int(e), int(cdiag), int(fr), int(first), int(ne)
    if ev != 'none':
        return ev
    thr = 12 if fr else 16
    if e < 5:
        return 'thin'
    if e < thr:
        return 'hold' if cdiag else ('rule4-1' if ne == 1 else 'rule4-n')
    return 'gate-s' if first else 'gate-other'


def eb(e):
    e = int(e)
    return '<5' if e < 5 else '5-7' if e < 8 else '8-11' if e < 12 else '12-15' if e < 16 else '16+'


rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
bane = [r for r in rows if r['name'].startswith('Bane') and int(r['replay']) >= 127810]
varsi = [r for r in rows if 'VarSi' in r['name'] and int(r['replay']) >= 127810]
par = collections.Counter()
for r in rows:
    if r['kind'] == 'parent':
        par[r['key']] += int(r['n'])
print('split parents (all colonies, all games):', dict(par))
LAB = ('hold', 'thin', 'rule4-1', 'rule4-n', 'gate-s', 'gate-other', 'split', 'eat', 'bitten', 'move', 'feed', 'unknown')


def sq_table(rs, title):
    c = collections.Counter()
    for r in rs:
        if r['kind'] != 'sq':
            continue
        f = r['key'].split('|')
        c[(r['window'], f[0])] += int(r['n'])
        if f[0] == 'lost':
            c[(r['window'], 'L', label(f))] += int(r['n'])
    print('\n## %s: contested square-ticks, lost share by our best neighbour\'s rule (%% of lost)' % title)
    print('w   won    lost   open  | ' + ' '.join('%7s' % l for l in LAB))
    for w in WS:
        lost = c[(w, 'lost')]
        print('%s %6d %6d %6d  | ' % (w, c[(w, 'won')], lost, c[(w, 'open')])
              + ' '.join('%7.1f' % (100.0 * c[(w, 'L', l)] / lost if lost else 0) for l in LAB))


def hold_detail(rs, title):
    c = collections.Counter()
    for r in rs:
        if r['kind'] != 'sq':
            continue
        f = r['key'].split('|')
        if f[0] != 'lost' or label(f) != 'hold':
            continue
        n = int(r['n'])
        geo = ('side' if f[4] == '1' else '') + ('+beyond' if f[5] == '1' else '')
        c[(r['window'], eb(f[2]), geo or 'diag-elsewhere', f[3] in 'UD')] += n
    print('\n## %s: lost squares in a hold, by energy x enemy beside s (side = on c\'s diagonal) x s up/down' % title)
    for w in WS:
        tot = sum(v for k, v in c.items() if k[0] == w)
        if not tot:
            continue
        parts = sorted(((v, k) for k, v in c.items() if k[0] == w), reverse=True)[:8]
        print(w, tot, ' | '.join('%s %s %s: %d' % (k[1], k[2], 'UD' if k[3] else 'LR', v) for v, k in parts))


def episodes(rs, title):
    c = collections.Counter()
    for r in rs:
        if r['kind'] != 'ep':
            continue
        ticks, h5, h8 = (int(x) for x in r['key'].split('|'))
        n = int(r['n'])
        w = r['window']
        c[(w, 'n')] += n
        c[(w, 'ticks')] += ticks * n
        c[(w, 'h5')] += (h5 > 0) * n
        c[(w, 'h8')] += (h8 > 0) * n
        c[(w, 'h5t')] += h5 * n
        c[(w, 'h8t')] += h8 * n
    print('\n## %s: lost-square episodes (ticks contested before the loss; hold ticks of the best neighbour)' % title)
    print('w  episodes  mean ticks before loss | episodes with a hold at e>=5 / e>=8 | hold ticks e>=5 / e>=8')
    for w in WS:
        n = c[(w, 'n')]
        if n:
            print('%s %8d %8.2f | %5d (%4.1f%%) / %5d (%4.1f%%) | %6d / %6d' % (
                w, n, c[(w, 'ticks')] / n, c[(w, 'h5')], 100.0 * c[(w, 'h5')] / n, c[(w, 'h8')],
                100.0 * c[(w, 'h8')] / n, c[(w, 'h5t')], c[(w, 'h8t')]))


def fills(rs, title):
    c = collections.Counter()
    for r in rs:
        if r['kind'] != 'fill':
            continue
        f = r['key'].split('|')
        tag, pe, rule = f[0], f[1], f[2]
        b1, a10, p10 = int(f[7]), int(f[8]), int(f[9])
        h10 = int(f[10]) if len(f) > 10 else 0
        geo = ('side' if f[4] == '1' else '') + ('+beyond' if f[5] == '1' else '') or 'none'
        n = int(r['n'])
        grp = 'Siect-F' if 'Siect' in r['rival'] else 'Yen' if ('VarSi' in r['rival'] or 'Cog' in r['rival']) else \
            'feeder' if r['rival'] in ('Colossus', 'medivac', 'NomNom2') else 'other'
        for key in ((r['window'], tag, rule, eb(pe), grp), (r['window'], tag, rule, eb(pe), 'all'),
                    (r['window'], tag, rule, eb(pe), 'enemy@s:' + geo)):
            c[key + ('n',)] += n
            c[key + ('b1',)] += b1 * n
            c[key + ('a10',)] += a10 * n
            c[key + ('p10',)] += p10 * n
            c[key + ('h10',)] += h10 * n
    print('\n## %s: fills of contested squares by split (parent rule x parent energy x rival group)' % title)
    print('w tag       rule  parent-e group (rival or enemy beside s)   n | child bitten 1st tick | child alive 10 |'
          ' parent alive 10 | square ours after 10')
    for k in sorted(k[:5] for k in c if k[5] == 'n'):
        n = c[k + ('n',)]
        if n >= 20 or k[4] == 'all':
            print('%s %-9s %-5s %-6s %-20s %5d | %5.1f | %5.1f | %5.1f | %5.1f' % (k + (n, 100.0 * c[k + ('b1',)] / n,
                  100.0 * c[k + ('a10',)] / n, 100.0 * c[k + ('p10',)] / n, 100.0 * c[k + ('h10',)] / n)))


def hold_view(rs, title, per_game=False):
    """review point: the hold's delay view over ALL contested squares (won / lost / open)."""
    c = collections.Counter()
    for r in rs:
        n = int(r['n'])
        g = r['replay'] if per_game else 'all'
        if r['kind'] == 'hct':
            e = int(r['key'])
            c[(g, r['window'], 'hct', '5-7' if e < 8 else '8-11')] += n
        elif r['kind'] == 'hep':
            res, ticks, h5, h8, e0 = (int(x) if i else x for i, x in enumerate(r['key'].split('|')))
            b = '5-7' if e0 < 8 else '8-11'
            for bb in (b, 'all'):
                c[(g, r['window'], 'ep', bb, res)] += n
                c[(g, r['window'], 'ept', bb, res)] += ticks * n
                c[(g, r['window'], 'eph', bb, res)] += h5 * n
    print('\n## %s: the hold over all contested squares (delay view)' % title)
    print('game   w | hold cell-ticks 5-7 / 8-11 | episodes with a hold, by energy at the first hold: n, won / lost / '
          'left %, mean contested ticks, mean hold ticks (won | lost | left)')
    for g in sorted(set(k[0] for k in c)):
        for w in WS:
            h57, h811 = c[(g, w, 'hct', '5-7')], c[(g, w, 'hct', '8-11')]
            if not (h57 or h811):
                continue
            parts = []
            for bb in ('5-7', '8-11', 'all'):
                ns = [c[(g, w, 'ep', bb, x)] for x in ('won', 'lost', 'left')]
                tot = sum(ns)
                if not tot:
                    continue
                mt = ' | '.join('%.1f/%.1f' % (c[(g, w, 'ept', bb, x)] / k, c[(g, w, 'eph', bb, x)] / k) if k else '-'
                                for x, k in zip(('won', 'lost', 'left'), ns))
                parts.append('%s n %d: %.0f / %.0f / %.0f%% (%s)' % (bb, tot, *(100.0 * k / tot for k in ns), mt))
            print('%-6s %s | %5d / %5d | %s' % (g, w, h57, h811, '; '.join(parts)))


sq_table(bane, 'Bane v2.2, all v2.2 games')
hold_view(bane, 'Bane v2.2, all v2.2 games')
hold_view([r for r in bane if r['replay'] in EQ], 'Bane v2.2, 5 equal-start VarSi losses, per game', per_game=True)
hold_detail(bane, 'Bane v2.2')
episodes(bane, 'Bane v2.2')
fills(bane, 'Bane v2.2')
for g in EQ:
    sq_table([r for r in bane if r['replay'] == g], 'Bane v2.2 in %s (equal-start VarSi loss)' % g)
    episodes([r for r in bane if r['replay'] == g], 'Bane v2.2 in %s' % g)
eqb = [r for r in bane if r['replay'] in EQ]
sq_table(eqb, 'Bane v2.2, 5 equal-start VarSi losses pooled')
episodes(eqb, 'Bane v2.2, 5 equal-start VarSi losses pooled')
fills(eqb, 'Bane v2.2, 5 equal-start VarSi losses pooled')
# VarSi raw (no rule labels): lost squares by event x energy bucket, and its fills
c = collections.Counter()
for r in varsi:
    if r['kind'] == 'sq':
        f = r['key'].split('|')
        if f[0] == 'lost':
            c[(r['window'], f[1], eb(f[2]))] += int(r['n'])
print('\n## VarSi raw: lost squares by event x energy (no rule labels)')
for w in WS:
    tot = sum(v for k, v in c.items() if k[0] == w)
    if tot:
        print(w, tot, ' | '.join('%s %s %.1f%%' % (k[1], k[2], 100.0 * v / tot)
                                 for v, k in sorted(((v, k) for k, v in c.items() if k[0] == w), reverse=True)[:8]))
fills(varsi, 'VarSi (raw rules: gate/rule4 labels are Bane\'s and do not apply)')
