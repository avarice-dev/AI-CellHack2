"""Pull 3: per-loss timeline and fight/refill numbers from tools/pull2/mine.py output (CH_PULL=pull3).
Reads data/pull3/mining/<id>.json (pop per tick, names, end) and races/<id>.csv.gz. Prints markdown.
Run: python -I tools/pull3/losses.py"""
import csv, glob, gzip, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'pull3', 'mining')
ME = 'Scourge'
TS = (50, 100, 200, 500, 1000)
W = ((0, 500), (500, 1000), (1000, 10 ** 9))
agg = {k: [0] * 8 for k in ('w0', 'w1', 'w2')}
print('| Match | Winner | ' + ' | '.join(f't{t} S/W' for t in TS) + ' | end S/W | S peak (tick) | S < 90% peak from | W passes S |')
print('|' + '---|' * (len(TS) + 6))
fights = []; growth = []
for jp in sorted(glob.glob(os.path.join(OUT, '[0-9]*.json'))):
    r = json.load(open(jp, encoding='utf-8'))
    names, pop, end = r['names'], r['pop'], r['end']
    s = names.index(ME)
    w = end['placement'].index(1) if 1 in end['placement'] else max(range(4), key=lambda c: end['pop'][c])
    if w == s:
        continue
    at = lambda t, c: pop[min(t, len(pop) - 1)][c]
    ps = [p[s] for p in pop]; pk = max(ps); tpk = ps.index(pk)
    t90 = next((t for t in range(tpk, len(ps)) if ps[t] < 0.9 * pk), None)
    tpass = next((t for t in range(len(pop)) if pop[t][w] > pop[t][s] and t > 20), None)
    cells = ' | '.join(f'{at(t, s)}/{at(t, w)}' for t in TS)
    print(f"| {r['id']} | {names[w]} | {cells} | {end['pop'][s]}/{end['pop'][w]} | {pk} ({tpk}) | {t90} | {tpass} |")
    # fights between S and W from the races file: deaths of S killed by W and of W killed by S, refill outcome
    f = dict(id=r['id'], wn=names[w])
    for i, (a, b) in enumerate(W):
        f[i] = dict(SbyW=0, WbyS=0, SbyW_refW=0, SbyW_refS=0, WbyS_refS=0, WbyS_refW=0, cont=0, contS=0, contW=0)
    with gzip.open(os.path.join(OUT, 'races', f"{r['id']}.csv.gz"), 'rt') as fh:
        for d in csv.DictReader(fh):
            d = {k: int(v) for k, v in d.items()}
            i = 0 if d['tDeath'] < 500 else 1 if d['tDeath'] < 1000 else 2
            g = f[i]; m = d['contMask']
            if d['deadCol'] == s and d['killerCol'] == w:
                g['SbyW'] += 1; g['SbyW_refW'] += d['fillCol'] == w; g['SbyW_refS'] += d['fillCol'] == s
            if d['deadCol'] == w and d['killerCol'] == s:
                g['WbyS'] += 1; g['WbyS_refS'] += d['fillCol'] == s; g['WbyS_refW'] += d['fillCol'] == w
            if m >> s & 1 and m >> w & 1 and d['deadCol'] in (s, w):
                g['cont'] += 1; g['contS'] += d['fillCol'] == s; g['contW'] += d['fillCol'] == w
    fights.append(f)
    reach = lambda c, n: next((t for t, p in enumerate(pop) if p[c] >= n), None)
    first_kill = None
    with gzip.open(os.path.join(OUT, 'races', f"{r['id']}.csv.gz"), 'rt') as fh:
        for d in csv.DictReader(fh):
            if int(d['deadCol']) == s and int(d['killerCol']) == w:
                first_kill = int(d['tDeath']); break     # rows are sorted by tDeath
    growth.append((r['id'], names[w], [reach(s, n) for n in (8, 32, 128, 512)], [reach(w, n) for n in (8, 32, 128, 512)], first_kill))
print('\nFights between Scourge (S) and the winner (W), per window t<500 / 500-1000 / >=1000.')
print('S-by-W: Scourge cells eaten to death by W (refilled by W / by S); W-by-S likewise; contested: squares freed by a')
print('death of S or W with both colonies adjacent, won by S / W.\n')
print('| Match | Winner | S-by-W (W/S refill) | W-by-S (S/W refill) | contested S/W of n |\n|---|---|---|---|---|')
tot = {i: dict.fromkeys(fights[0][0], 0) for i in range(3)} if fights else {}
for f in fights:
    c = lambda key, fmt: ' / '.join(fmt(f[i]) for i in range(3))
    print(f"| {f['id']} | {f['wn']} | {c(0, lambda g: f'{g['SbyW']} ({g['SbyW_refW']}/{g['SbyW_refS']})')} | "
          f"{c(0, lambda g: f'{g['WbyS']} ({g['WbyS_refS']}/{g['WbyS_refW']})')} | "
          f"{c(0, lambda g: f'{g['contS']}/{g['contW']} of {g['cont']}')} |")
    for i in range(3):
        for k in tot[i]: tot[i][k] += f[i][k]
for i in range(3):
    g = tot[i]
    print(f"\nWindow {i}: S-by-W {g['SbyW']} (refilled W {g['SbyW_refW']}, S {g['SbyW_refS']}); W-by-S {g['WbyS']} "
          f"(refilled S {g['WbyS_refS']}, W {g['WbyS_refW']}); contested {g['cont']}: S {g['contS']}, W {g['contW']}")
print('\nGrowth: first tick each colony reaches pop 8 / 32 / 128 / 512; first Scourge cell killed by the winner.\n')
print('| Match | Winner | Scourge | Winner | first S-by-W kill |\n|---|---|---|---|---|')
for g in growth:
    print(f'| {g[0]} | {g[1]} | {" / ".join(map(str, g[2]))} | {" / ".join(map(str, g[3]))} | {g[4]} |')
print('\nEarly births (t < 200), every colony in the 15 replays pooled by name: births, child energy median and share of'
      ' children with energy 2, moves.\n')
import statistics, collections
pool = collections.defaultdict(lambda: [collections.Counter(), 0, 0])     # name -> [childE counter, moves, replays]
for jp in sorted(glob.glob(os.path.join(OUT, '[0-9]*.json'))):
    r = json.load(open(jp, encoding='utf-8'))
    for c, n in enumerate(r['names']):
        pool[n][2] += 1
    for k, v in r.get('early', {}).items():
        c, kind, e = k.split(','); n = r['names'][int(c)]
        if kind == 'b': pool[n][0][int(e)] += v
        else: pool[n][1] += v
print('| Colony | replays | births/replay | child e median | child e=2 % | child e>=8 % | moves/replay |\n|---|---|---|---|---|---|---|')
for n, (ce, mv, k) in sorted(pool.items(), key=lambda kv: -kv[1][2]):
    tot = sum(ce.values()) or 1
    med = statistics.median([e for e, v in ce.items() for _ in range(v)]) if ce else None
    print(f'| {n} | {k} | {tot // k} | {med} | {100 * ce[2] / tot:.0f} | {100 * sum(v for e, v in ce.items() if e >= 8) / tot:.0f} | {mv // k} |')
