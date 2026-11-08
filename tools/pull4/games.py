"""Pull 4: per-game timeline, growth, fights/refills and early child energy for Contagion (C), Scourge (S, when present)
and the key rival X (the winner when C lost, the runner-up when C won), from tools/pull2/mine.py output (CH_PULL=pull4).
Same measures as tools/pull3/losses.py. Reads data/pull4/mining/<id>.json and races/<id>.csv.gz. Prints markdown.
Run: python -I tools/pull4/games.py"""
import collections, csv, glob, gzip, json, os, statistics
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'pull4', 'mining')
ME, RIVAL = 'Contagion', 'Scourge'
TS = (50, 100, 200, 500, 1000)
games = []
for jp in sorted(glob.glob(os.path.join(OUT, '[0-9]*.json'))):
    r = json.load(open(jp, encoding='utf-8'))
    names, pop, end = r['names'], r['pop'], r['end']
    pl = end['placement']
    c = names.index(ME)
    s = names.index(RIVAL) if RIVAL in names else None
    won = pl[c] == 1
    x = pl.index(2) if won else pl.index(1)
    at = lambda t, k: pop[min(t, len(pop) - 1)][k]
    reach = lambda k, n: next((t for t, p in enumerate(pop) if p[k] >= n), None)
    fx = [dict(CbyX=0, CbyX_refC=0, CbyX_refX=0, XbyC=0, XbyC_refC=0, XbyC_refX=0) for _ in range(3)]
    first_kill = None
    with gzip.open(os.path.join(OUT, 'races', f"{r['id']}.csv.gz"), 'rt') as fh:
        for d in csv.DictReader(fh):
            d = {k: int(v) for k, v in d.items()}
            i = 0 if d['tDeath'] < 500 else 1 if d['tDeath'] < 1000 else 2
            g = fx[i]
            if d['deadCol'] == c and d['killerCol'] == x:
                g['CbyX'] += 1; g['CbyX_refC'] += d['fillCol'] == c; g['CbyX_refX'] += d['fillCol'] == x
                if first_kill is None:
                    first_kill = d['tDeath']
            if d['deadCol'] == x and d['killerCol'] == c:
                g['XbyC'] += 1; g['XbyC_refC'] += d['fillCol'] == c; g['XbyC_refX'] += d['fillCol'] == x
    games.append(dict(id=r['id'], won=won, place=pl[c], names=names, c=c, s=s, x=x, pl=pl,
                      pops={k: [at(t, k) for t in TS] + [end['pop'][k]] for k in range(len(names))},
                      reach={k: [reach(k, n) for n in (32, 128, 512)] for k in range(len(names))},
                      fx=fx, first_kill=first_kill, early=r.get('early', {})))

fmt = lambda v: '-' if v is None else str(v)
for won in (True, False):
    gs = [g for g in games if g['won'] == won]
    print(f"\n### Contagion {'wins' if won else 'losses'} ({len(gs)})\n")
    print('Pops C / S / X (S = Scourge, "-" if absent; X = ' + ('runner-up' if won else 'winner') + ').\n')
    print('| Match | C place | X | S place | ' + ' | '.join(f't{t}' for t in TS) + ' | end | C t500->end |')
    print('|' + '---|' * (len(TS) + 6))
    for g in gs:
        cells = []
        for i in range(len(TS) + 1):
            sv = g['pops'][g['s']][i] if g['s'] is not None else '-'
            cells.append(f"{g['pops'][g['c']][i]}/{sv}/{g['pops'][g['x']][i]}")
        late = g['pops'][g['c']][-1] - g['pops'][g['c']][3]
        sp = g['pl'][g['s']] if g['s'] is not None else '-'
        print(f"| {g['id']} | {g['place']} | {g['names'][g['x']]} | {sp} | " + ' | '.join(cells) + f' | {late:+d} |')

print('\nGrowth: first tick reaching pop 32 / 128 / 512.\n')
print('| Match | C result | Contagion | Scourge | X (name) | first C cell killed by X |\n|---|---|---|---|---|---|')
for g in games:
    rs = lambda k: ' / '.join(map(fmt, g['reach'][k])) if k is not None else '-'
    print(f"| {g['id']} | {'win' if g['won'] else 'loss ' + str(g['place'])} | {rs(g['c'])} | {rs(g['s'])} | "
          f"{rs(g['x'])} ({g['names'][g['x']]}) | {fmt(g['first_kill'])} |")

med = lambda xs: statistics.median(xs) if xs else None
print('\nMedians: ticks to 128 / 512 (over games that reached the mark), pop at t100 / t200')
for lab, sel in (('Contagion, all', lambda g: [g['c']]),
                 ('Contagion, wins', lambda g: [g['c']] if g['won'] else []),
                 ('Contagion, losses', lambda g: [] if g['won'] else [g['c']]),
                 ('Scourge (these games)', lambda g: [g['s']] if g['s'] is not None else []),
                 ('X = winner in C losses', lambda g: [] if g['won'] else [g['x']]),
                 ('X = runner-up in C wins', lambda g: [g['x']] if g['won'] else [])):
    ks = [(g, k) for g in games for k in sel(g)]
    if not ks:
        continue
    a = [g['reach'][k][1] for g, k in ks if g['reach'][k][1] is not None]
    b = [g['reach'][k][2] for g, k in ks if g['reach'][k][2] is not None]
    t100 = [g['pops'][k][1] for g, k in ks]
    t200 = [g['pops'][k][2] for g, k in ks]
    print(f'- {lab}: n={len(ks)}; 128 at {med(a)} (range {min(a) if a else "-"}-{max(a) if a else "-"}); 512 at {med(b)} '
          f'(range {min(b) if b else "-"}-{max(b) if b else "-"}, reached in {len(b)}); pop t100 median {med(t100)}, t200 {med(t200)}')

print('\nFights Contagion (C) vs X per window t<500 / 500-1000 / >=1000: C-by-X = C cells eaten to death by X '
      '(refilled by C / X); X-by-C likewise.\n')
print('| Match | X | C-by-X (C/X refill) | X-by-C (C/X refill) |\n|---|---|---|---|')
tot = {won: [collections.Counter() for _ in range(3)] for won in (True, False)}
for g in games:
    f = g['fx']
    a = ' / '.join(f"{w['CbyX']} ({w['CbyX_refC']}/{w['CbyX_refX']})" for w in f)
    b = ' / '.join(f"{w['XbyC']} ({w['XbyC_refC']}/{w['XbyC_refX']})" for w in f)
    print(f"| {g['id']} | {g['names'][g['x']]} | {a} | {b} |")
    for i in range(3):
        tot[g['won']][i].update(f[i])
for won in (True, False):
    for i, lab in enumerate(('t<500', '500-1000', '>=1000')):
        w = tot[won][i]
        print(f"- {'wins' if won else 'losses'} {lab}: C-by-X {w['CbyX']} (refilled C {w['CbyX_refC']}, X {w['CbyX_refX']}); "
              f"X-by-C {w['XbyC']} (refilled C {w['XbyC_refC']}, X {w['XbyC_refX']})")

print('\nEarly births (t < 200) pooled by colony name over the decoded games: births per replay, child energy median, '
      'share of children with e = 2 and e >= 8, moves per replay.\n')
pool = collections.defaultdict(lambda: [collections.Counter(), 0, 0])
for g in games:
    for n in g['names']:
        pool[n][2] += 1
    for k, v in g['early'].items():
        ci, kind, e = k.split(',')
        n = g['names'][int(ci)]
        if kind == 'b':
            pool[n][0][int(e)] += v
        else:
            pool[n][1] += v
print('| Colony | replays | births/replay | child e median | child e=2 % | child e>=8 % | moves/replay |\n|---|---|---|---|---|---|---|')
for n, (ce, mv, k) in sorted(pool.items(), key=lambda kv: -kv[1][2]):
    tt = sum(ce.values()) or 1
    md = statistics.median([e for e, v in ce.items() for _ in range(v)]) if ce else None
    print(f'| {n} | {k} | {tt // k} | {md} | {100 * ce[2] / tt:.0f} | {100 * sum(v for e, v in ce.items() if e >= 8) / tt:.0f} | {mv // k} |')
for n in (ME, RIVAL):
    if n in pool:
        print(f'\n{n} child energy histogram (t < 200, these games): ' + ', '.join(f'{e}:{v}' for e, v in sorted(pool[n][0].items())))
