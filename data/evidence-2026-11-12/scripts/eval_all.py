"""Scratch: complete-picture evaluation of Bane, every game stage, Bane vs the colony that decided the game
(winner when Bane lost, runner-up when Bane won).  Joins review.py rows, front.py rows (full columns) and the
solo curve of our opening from each start square.
Usage: python eval_all.py <solo.csv> <out.csv> --rev <csv> [...] --front <csv> [...] --group NAME=id,id,... [...]
Prints per group: mean of each measure for Bane and for the deciding rival, the difference, and the share of
games where Bane was better; then Spearman of each Bane measure (and Bane minus rival) with Bane's final share.
"""
import csv
import json
import sys
from collections import defaultdict

args = sys.argv[1:]
solo_path, out_path = args[0], args[1]
mode, revs, fronts, groups = None, [], [], {}
for a in args[2:]:
    if a in ('--rev', '--front', '--group'):
        mode = a
    elif mode == '--rev':
        revs.append(a)
    elif mode == '--front':
        fronts.append(a)
    elif mode == '--group':
        k, v = a.split('=', 1)
        groups[k] = [x for x in v.split(',') if x]

solo = {(int(r['x']), int(r['y'])): r for r in csv.DictReader(open(solo_path))}
rev = defaultdict(dict)                       # replay -> colony -> row (last file wins)
for f in revs:
    for r in csv.DictReader(open(f, encoding='utf-8')):
        rev[r['replay']][int(r['colony'])] = r
front = defaultdict(dict)
for f in fronts:
    for r in csv.DictReader(open(f, encoding='utf-8')):
        if 'ct_a' in r:                         # only full-column runs
            front[r['replay']][int(r['colony'])] = r


def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def measures(rid, c, o, rs, fs):
    """Measures for colony c; o = the other colony of the pair (for pair measures)."""
    r, f = rs[c], fs.get(c, {})
    m = {}
    s = solo.get((int(r['x']), int(r['y'])))
    # 1 start
    m['1 wall'] = fl(r['wall'])
    m['1 near'] = fl(r['near'])
    m['1 solo60'] = fl(s['s60']) if s else None
    m['1 solo100'] = fl(s['s100']) if s else None
    # 2 opening
    m['2 p30'] = fl(r['p30'])
    m['2 p60'] = fl(r['p60'])
    m['2 g30'] = fl(r['p30']) / fl(s['s30']) if s else None
    m['2 g60'] = fl(r['p60']) / fl(s['s60']) if s else None
    m['2 g100'] = fl(r['p100']) / fl(s['s100']) if s else None
    for w in ('t0', 't30'):
        for k in ('split', 'move', 'hold', 'feed', 'contact'):
            m['2 %s_%s' % (w, k)] = fl(r['%s_%s' % (w, k)])
    # 3 first contact with the pair rival
    if f:
        first = json.loads(f['first'])
        closed = json.loads(f['closed'])
        m['3 first_any'] = min([v for v in first.values() if v >= 0] or [None]) if any(
            v >= 0 for v in first.values()) else None
        fo = first.get(str(o), -1)
        m['3 first_pair'] = fo if fo >= 0 else None
        m['3 closed_pair'] = 1.0 if closed.get(str(o)) else 0.0 if fo >= 0 else None
    # 4 front bite order (all ticks)
    if f:
        for k in ('fr_eat', 'fr_bitten', 'on_eat', 'on_bitten', 'c_eat', 'c_bitten', 'c_none', 'none_lo',
                  'c_split', 'c_move', 'c_feed'):
            m['4 ' + k] = fl(f[k])
        m['4 fr_n'] = fl(f['fr'])
        bo, bb = json.loads(f['bites_on']), json.loads(f['bitten_by'])
        m['4 bites_on_pair'] = fl(bo.get(str(o)))
        m['4 bitten_by_pair'] = fl(bb.get(str(o)))
        tot = (m['4 bites_on_pair'] or 0) + (m['4 bitten_by_pair'] or 0)
        m['4 bite_share_pair'] = 100 * m['4 bites_on_pair'] / tot if tot else None
    for w in ('t30', 't60', 't100', 't200'):
        m['4 %s_bitfirst' % w] = fl(r['%s_bitfirst' % w])
    # 5 front land
    for w in ('t30', 't60', 't100', 't200'):
        for k in ('take', 'retake', 'deaths'):
            m['5 %s_%s' % (w, k)] = fl(r['%s_%s' % (w, k)])
    if f:
        for k in ('took', 'took_e', 'took_e4', 'took_dead5'):
            m['5 ' + k] = fl(f[k])
        for w in ('a', 'b', 'c'):
            m['5 ctw_' + w] = fl(f['ctw_' + w])
            m['5 ctl_' + w] = fl(f['ctl_' + w])
            m['5 ct_' + w] = fl(f['ct_' + w])
        tf = json.loads(f['took_from'])
        m['5 took_from_pair'] = fl(tf.get(str(o)))
        # 7 third colonies: squares taken from colonies other than the pair rival
        m['7 took_third'] = sum(v for k, v in tf.items() if k != str(o))
        bo = json.loads(f['bites_on'])
        m['7 bites_third'] = sum(v for k, v in bo.items() if k != str(o))
    # 6 interior
    for w in ('t60', 't100', 't200'):
        for k in ('feed', 'capidle', 'hold', 'split', 'move', 'contact'):
            m['6 %s_%s' % (w, k)] = fl(r['%s_%s' % (w, k)])
    # 7 growth after t100
    m['7 gain100_200'] = fl(r['p200']) - fl(r['p100'])
    m['7 gain200_500'] = fl(r['p500']) - fl(r['p200'])
    m['7 gain500_end'] = fl(r['final']) - fl(r['p500'])
    # 8 late
    for w in ('p100', 'p200', 'p500', 'final'):
        m['8 ' + w] = fl(r[w])
    return m


rows_out = []
SIGN = {}                                    # measure -> +1 if higher is better for the colony (for 'better' share)
for gname, ids in groups.items():
    per = []
    for rid in ids:
        rs = rev.get(rid)
        if not rs:
            print('no review row', gname, rid)
            continue
        fs = front.get(rid, {})
        b = [c for c, r in rs.items() if r['name'].startswith('Bane')]
        if len(b) != 1:
            print('skip (Bane colonies %d)' % len(b), rid)
            continue
        b = b[0]
        tot = sum(int(r['final']) for r in rs.values()) or 1
        order = sorted(rs, key=lambda c: -int(rs[c]['final']))
        won = order[0] == b
        o = order[1] if won else order[0]
        mb, mo = measures(rid, b, o, rs, fs), measures(rid, o, b, rs, fs)
        per.append((rid, won, int(rs[b]['final']) / tot, rs[o]['name'], mb, mo))
        row = dict(group=gname, replay=rid, won=int(won), share=round(int(rs[b]['final']) / tot, 3),
                   rival=rs[o]['name'], has_front=int(bool(fs)))
        for k, v in mb.items():
            row['B ' + k] = v
            row['R ' + k] = mo.get(k)
        rows_out.append(row)
    if not per:
        continue
    keys = sorted({k for p in per for k in p[4]})
    nw = sum(p[1] for p in per)
    print('\n## %s: %d games, Bane won %d; front rows %d' % (gname, len(per), nw, sum(1 for p in per if p[4].get('4 c_eat') is not None)))
    for sub, sel in (('all', lambda p: True), ('won', lambda p: p[1]), ('lost', lambda p: not p[1])):
        ps = [p for p in per if sel(p)]
        if not ps:
            continue
        print('\n### %s (%d) - measure: Bane mean | rival mean | mean(B-R) | B>R share' % (sub, len(ps)))
        for k in keys:
            pairs = [(p[4].get(k), p[5].get(k)) for p in ps]
            pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
            if not pairs:
                continue
            mb = sum(x for x, _ in pairs) / len(pairs)
            mr = sum(y for _, y in pairs) / len(pairs)
            gt = sum(1 for x, y in pairs if x > y) / len(pairs)
            print('%-22s %9.2f | %9.2f | %+9.2f | %4.0f%%  (n %d)' % (k, mb, mr, mb - mr, 100 * gt, len(pairs)))

def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** .5
    db = sum((y - mb) ** 2 for y in rb) ** .5
    return num / (da * db) if da and db else 0.0


uniq = {r['replay']: r for r in rows_out}.values()
mk = sorted({k[2:] for r in uniq for k in r if k.startswith('B ')})
print('\n## all games (%d): Spearman with Bane final share - Bane measure | Bane minus rival' % len(uniq))
res = []
for k in mk:
    pts = [(r['B ' + k], r.get('R ' + k), r['share']) for r in uniq if r.get('B ' + k) is not None]
    if len(pts) < 8:
        continue
    s1 = spearman([p[0] for p in pts], [p[2] for p in pts])
    d = [(p[0] - p[1], p[2]) for p in pts if p[1] is not None]
    s2 = spearman([x for x, _ in d], [y for _, y in d]) if len(d) >= 8 else 0.0
    res.append((k, s1, s2, len(pts)))
for k, s1, s2, n in sorted(res, key=lambda t: -max(abs(t[1]), abs(t[2]))):
    print('%-22s %+.2f | %+.2f  (n %d)' % (k, s1, s2, n))

if rows_out:
    fields = []
    for r in rows_out:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(out_path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)
    print('\nwrote', out_path, len(rows_out))
