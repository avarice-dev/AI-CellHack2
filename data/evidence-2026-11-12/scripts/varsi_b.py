"""Scratch: Bane v2.2 vs VarSi in the VarSi games of eval-all.csv, action budget by situation (budget.csv).
Usage: python varsi_b.py <budget.csv> <window> [rival keyword] [replay:label ...]   (default VarSi and its 11 games;
the pooled row takes the 'L eq' games, or every label starting with 'L' when none is 'L eq')
Per game and colony: share of cell-ticks in each situation (open-far, open-near, open-front, boxed), and within open
cells with energy >= 5: split / move / none shares (none = rest, hold, or a split / move that lost the square)."""
import csv, collections, sys
G = {'129850': 'W good', '131102': 'W good', '131312': 'W good', '129308': 'L eq', '130482': 'L eq', '130818': 'L eq',
     '131265': 'L eq', '131276': 'L eq', '131114': 'L bad', '130915': 'L bad', '130988': 'L bad'}
win = sys.argv[2]
RIV = sys.argv[3] if len(sys.argv) > 3 else 'VarSi'
if len(sys.argv) > 4:
    G = dict(a.split(':', 1) for a in sys.argv[4:])
d = collections.defaultdict(collections.Counter)
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8')):
    if r['replay'] not in G or r['window'] != win:
        continue
    who = 'B' if r['name'].startswith('Bane') else 'V' if RIV in r['name'] else None
    if not who:
        continue
    n = int(r['n'])
    c = d[(r['replay'], who)]
    if r['act'] == 'unknown':
        c['unknown'] += n
        continue
    if r['act'] == 'split':
        c['splits'] += n
    c['all'] += n
    sit = 'boxed' if r['space'] == 'boxed' else 'o-' + r['enemy']
    c[sit] += n
    if r['space'] == 'open' and r['energy'] != '<5':
        c[(sit, 'n5')] += n
        c[(sit, r['act'])] += n
        c[('open5', r['act'])] += n
        c[('open5', 'n5')] += n
    if r['space'] == 'open' and r['energy'] == '<5':
        c['open<5'] += n
    if r['space'] == 'open' and r['enemy'] in ('near', 'front') and r['act'] == 'none' and r['energy'] != '<5':
        # review point: Bane v2.2 rule of an eligible near/front 'none' (diag column from budget.py 2026-11-12)
        dg = r.get('diag', '?')
        lab = ('12+' if r['energy'] != '5-11' else 'hold' if dg == '1' else 'rule4-fail' if dg == '0' else '?')
        c[('nonelab', r['enemy'], lab)] += n
def pc(a, b): return '%5.1f' % (100.0 * a / b) if b else '    -'
print('rival', RIV, '| window', win, '| share of cell-ticks: o-far o-near o-front boxed open<5 | open e>=5: split move none (all) | far: split none | near: split none | front: eat stunned')
for rid in G:
    for who in 'BV':
        c = d[(rid, who)]
        if not c['all']:
            continue
        a = c['all']
        print('%s %-6s %s %6d |' % (rid, G[rid], who, a),
              ' '.join(pc(c[k], a) for k in ('o-far', 'o-near', 'o-front', 'boxed', 'open<5')), '|',
              ' '.join(pc(c[('open5', k)], c[('open5', 'n5')]) for k in ('split', 'move', 'none')), '|',
              ' '.join(pc(c[('o-far', k)], c[('o-far', 'n5')]) for k in ('split', 'none')), '|',
              ' '.join(pc(c[('o-near', k)], c[('o-near', 'n5')]) for k in ('split', 'none')), '|',
              ' '.join(pc(c[('o-front', k)], c[('o-front', 'n5')]) for k in ('eat', 'stunned')))

# review point: eligible cells (open, e >= 5), their splits, and Bane's splits at VarSi's rate.
# 'extra' is an UPPER BOUND: a cell that fails to split stays eligible next tick, so Bane's n is inflated by its own
# holds and failed splits.  The plain split share per cell-tick (all live cells) is printed beside it.
EQL = [g for g in G if G[g] == 'L eq'] or [g for g in G if G[g].startswith('L')]
for title, sits in (('near+front', ('o-near', 'o-front')), ('far', ('o-far',))):
    print()
    print('window', win, '| eligible %s (open, e>=5): Bane n / splits / rate | VarSi rate | Bane splits at VarSi rate |'
          ' extra (upper bound) | Bane total splits | extra / total | split share per cell-tick B / V | unknown B / V' % title)
    pool = collections.Counter()
    for rid in G:
        b, v = d[(rid, 'B')], d[(rid, 'V')]
        if not b['all']:
            continue
        bn = sum(b[(k, 'n5')] for k in sits)
        bs = sum(b[(k, 'split')] for k in sits)
        vn = sum(v[(k, 'n5')] for k in sits)
        vs = sum(v[(k, 'split')] for k in sits)
        if rid in EQL:
            for k, x in (('bn', bn), ('bs', bs), ('vn', vn), ('vs', vs), ('bt', b['splits']), ('ba', b['all']),
                         ('vt', v['splits']), ('va', v['all'])):
                pool[k] += x
        vr = vs / vn if vn else 0
        at = bn * vr
        print('%s %-6s | %5d %4d %5.1f%% | %5.1f%% | %6.0f | %+5.0f | %5d | %5.1f%% | %4.1f%% / %4.1f%% | %d / %d' % (
            rid, G[rid], bn, bs, 100.0 * bs / bn if bn else 0, 100 * vr, at, at - bs, b['splits'],
            100.0 * (at - bs) / b['splits'] if b['splits'] else 0, 100.0 * b['splits'] / b['all'],
            100.0 * v['splits'] / v['all'] if v['all'] else 0, b['unknown'], v['unknown']))
    vr = pool['vs'] / pool['vn'] if pool['vn'] else 0
    at = pool['bn'] * vr
    print('%d %s pooled |' % (len(EQL), 'eq-start losses' if G[EQL[0]] == 'L eq' else 'losses'), '%5d %4d %5.1f%% | %5.1f%% | %6.0f | %+5.0f | %5d | %5.1f%% | %4.1f%% / %4.1f%%' % (
        pool['bn'], pool['bs'], 100.0 * pool['bs'] / max(pool['bn'], 1), 100 * vr, at, at - pool['bs'], pool['bt'],
        100.0 * (at - pool['bs']) / max(pool['bt'], 1), 100.0 * pool['bt'] / max(pool['ba'], 1),
        100.0 * pool['vt'] / max(pool['va'], 1)))
    if win == 'a':
        print('(window a: per-game n is small; use the pooled row only)')

# review point: Bane's eligible near / front 'none' cell-ticks by its v2.2 rule.  hold = 5-11 with a diagonal
# enemy (the gate wait); rule4-fail = 5-11 without one (rule 4's split / walk lost the square); 12+ = energy 12 or more.
print()
print('window', win, '| Bane eligible none (open, e>=5) by rule: near hold / rule4-fail / 12+ | front hold / rule4-fail / 12+ (12+ = gate wait or rule 4 at threshold 16; budget buckets cannot split it)  (cell-ticks)')
for rid in G:
    b = d[(rid, 'B')]
    if b['all']:
        print('%s %-6s |' % (rid, G[rid]), ' '.join('%5d' % b[('nonelab', 'near', l)] for l in ('hold', 'rule4-fail', '12+')),
              '|', ' '.join('%5d' % b[('nonelab', 'front', l)] for l in ('hold', 'rule4-fail', '12+')),
              '| unlabelled %d' % (b[('nonelab', 'near', '?')] + b[('nonelab', 'front', '?')]))
