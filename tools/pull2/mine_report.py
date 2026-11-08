"""Aggregate tools/pull2/mine.py output (data/pull2/mining/*.json and races/*.csv.gz) per cell name.
Writes data/pull2/mining/refill.json, data/pull2/mining/rest.json and prints markdown tables to stdout.
Usage: python -I tools/pull2/mine_report.py > tables.md
"""
import csv, gzip, glob, json, os, statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'pull2', 'mining')
DT_BINS = [(0, 0), (1, 1), (2, 2), (3, 5), (6, 10), (11, 50), (51, 10 ** 9)]
E_BINS = [(0, 2), (3, 3), (4, 5), (6, 8), (9, 16), (17, 24), (25, 25), (26, 255)]
WN = ['t0-500', 't500-1000', 't1000-end']
ATOM = ('AtomPush', 'AtomCrasher')


def bins(vals, B):
    n = len(vals) or 1
    return [round(100 * sum(1 for v in vals if a <= v <= b) / n, 1) for a, b in B]


def lab(B):
    return [f'{a}' if a == b else (f'>{a - 1}' if b > 999 else f'{a}-{b}') for a, b in B]


def med(v):
    return st.median(v) if v else None


def load():
    reps = {}
    for jp in sorted(glob.glob(os.path.join(OUT, '[0-9]*.json'))):
        r = json.load(open(jp, encoding='utf-8'))
        rows = []
        with gzip.open(os.path.join(OUT, 'races', f"{r['id']}.csv.gz"), 'rt') as f:
            for d in csv.DictReader(f):
                rows.append({k: int(v) for k, v in d.items()})
        reps[r['id']] = (r, rows)
    return reps


def refill(reps):
    fill = defaultdict(lambda: dict(dt=[], e=[], moves=0, wins=0))      # by filler name, all refills
    cont = defaultdict(lambda: dict(n=0, won=0, dtWon=[], eWon=[], lostDt=[], unfilled=0, replays=set()))  # contested
    deadby = defaultdict(lambda: dict(n=0, own=0, killer=0, other=0, unfilled=0, dt=[]))   # by name of the dead cell
    pair = defaultdict(lambda: dict(n=0, sprint=0, atom=0, other=0, unfilled=0, dtS=[], dtA=[], eS=[], eA=[]))
    for rid, (r, rows) in reps.items():
        nm = r['names']
        sprint = [c for c in range(4) if nm[c] == 'Sprint']
        atoms = [c for c in range(4) if nm[c] in ATOM]
        for d in rows:
            fc, dc, kc, m = d['fillCol'], d['deadCol'], d['killerCol'], d['contMask']
            cs = [c for c in range(4) if m >> c & 1]
            if fc >= 0:
                f = fill[nm[fc]]; f['dt'].append(d['dt']); f['wins'] += 1
                if d['fillKind'] == 1:
                    f['e'].append(d['fillE'])
                else:
                    f['moves'] += 1
            b = deadby[nm[dc]]; b['n'] += 1
            if fc < 0:
                b['unfilled'] += 1
            else:
                b['dt'].append(d['dt'])
                if fc == dc:
                    b['own'] += 1
                elif fc == kc:
                    b['killer'] += 1
                else:
                    b['other'] += 1
            if len(cs) >= 2:
                for c in cs:
                    o = cont[nm[c]]; o['n'] += 1; o['replays'].add(rid)
                    if fc < 0:
                        o['unfilled'] += 1
                    elif fc == c:
                        o['won'] += 1; o['dtWon'].append(d['dt'])
                        if d['fillKind'] == 1:
                            o['eWon'].append(d['fillE'])
                    else:
                        o['lostDt'].append(d['dt'])
                for s in sprint:
                    for a in atoms:
                        if s in cs and a in cs:
                            w = 0 if d['tDeath'] < 500 else 1 if d['tDeath'] < 1000 else 2
                            for key in (f'{nm[a]}|{WN[w]}', f'{nm[a]}|all', f'{rid} {nm[a]}|all'):
                                p = pair[key]; p['n'] += 1
                                if fc < 0:
                                    p['unfilled'] += 1
                                elif fc == s:
                                    p['sprint'] += 1; p['dtS'].append(d['dt'])
                                    if d['fillKind'] == 1:
                                        p['eS'].append(d['fillE'])
                                elif fc == a:
                                    p['atom'] += 1; p['dtA'].append(d['dt'])
                                    if d['fillKind'] == 1:
                                        p['eA'].append(d['fillE'])
                                else:
                                    p['other'] += 1
    return fill, cont, deadby, pair


def rest(reps):
    agg = defaultdict(lambda: [[0] * 6 for _ in range(3)])   # name -> w -> [z, plus1, other, plus1_belowcap, freeBelowCap, touched]
    inc = defaultdict(lambda: [[] for _ in range(3)])         # name -> w -> per-replay +1 gains per tick
    share_r = defaultdict(lambda: [[] for _ in range(3)])
    for rid, (r, _) in reps.items():
        T = r['ticks']
        wt = [min(T, 500), max(0, min(T, 1000) - 500), max(0, T - 1000)]
        for c in range(4):
            nm = r['names'][c]
            for w in range(3):
                h = r['rest'][str(c)].get(str(w), {})
                z = sum(v[0] for v in h.values()); p1 = sum(v[1] for v in h.values()); ot = sum(v[2] for v in h.values())
                bc = sum(v[1] for q, v in h.items() if int(q) < 50); fb = sum(sum(v) for q, v in h.items() if int(q) < 50)
                a = agg[nm][w]; a[0] += z; a[1] += p1; a[2] += ot; a[3] += bc; a[4] += fb; a[5] += r['touched'][c * 3 + w]
                if wt[w] and z + p1 + ot > 0:
                    inc[nm][w].append(p1 / wt[w]); share_r[nm][w].append(p1 / (z + p1 + ot))
    return agg, inc, share_r


def main():
    reps = load()
    fill, cont, deadby, pair = refill(reps)
    agg, inc, share_r = rest(reps)
    names = sorted(fill, key=lambda n: -fill[n]['wins'])
    print('### (a1) All refills of death-freed squares, by the colony that took the square\n')
    print('| cell | refills | median ticks | ' + ' | '.join(f'dt {x} %' for x in lab(DT_BINS)) + ' | by move % | median child E | ' + ' | '.join(f'E {x} %' for x in lab(E_BINS)) + ' |')
    print('|' + '---|' * (5 + len(DT_BINS) + len(E_BINS)))
    jfill = {}
    for n in names:
        f = fill[n]
        jfill[n] = dict(refills=f['wins'], medianDt=med(f['dt']), dtPct=dict(zip(lab(DT_BINS), bins(f['dt'], DT_BINS))),
                        movePct=round(100 * f['moves'] / f['wins'], 1), medianChildE=med(f['e']), childEPct=dict(zip(lab(E_BINS), bins(f['e'], E_BINS))))
        print(f"| {n} | {f['wins']} | {med(f['dt'])} | " + ' | '.join(map(str, bins(f['dt'], DT_BINS))) + f" | {jfill[n]['movePct']} | {med(f['e'])} | " + ' | '.join(map(str, bins(f['e'], E_BINS))) + ' |')
    print('\n### (a2) Contested races (>= 2 colonies orthogonally adjacent to the square at the death), by contender\n')
    print('| cell | replays | races | won % | lost % | unfilled % | median ticks when won | median ticks when lost | median child E when won |')
    print('|---|---|---|---|---|---|---|---|---|')
    jcont = {}
    for n in sorted(cont, key=lambda n: -cont[n]['won'] / max(1, cont[n]['n'])):
        o = cont[n]; N = o['n']
        lost = N - o['won'] - o['unfilled']
        jcont[n] = dict(replays=len(o['replays']), races=N, wonPct=round(100 * o['won'] / N, 1), lostPct=round(100 * lost / N, 1),
                        unfilledPct=round(100 * o['unfilled'] / N, 1), medianDtWon=med(o['dtWon']), medianDtLost=med(o['lostDt']), medianChildEWon=med(o['eWon']))
        j = jcont[n]
        print(f"| {n} | {j['replays']} | {N} | {j['wonPct']} | {j['lostPct']} | {j['unfilledPct']} | {j['medianDtWon']} | {j['medianDtLost']} | {j['medianChildEWon']} |")
    print('\n### (a3) Who takes the square, by the dead cell\'s colony\n')
    print('| dead cell | deaths | own colony % | killer % | third colony % | unfilled % | median ticks |')
    print('|---|---|---|---|---|---|---|')
    jdead = {}
    for n in sorted(deadby, key=lambda n: -deadby[n]['n']):
        b = deadby[n]; N = b['n']
        jdead[n] = dict(deaths=N, ownPct=round(100 * b['own'] / N, 1), killerPct=round(100 * b['killer'] / N, 1), otherPct=round(100 * b['other'] / N, 1),
                        unfilledPct=round(100 * b['unfilled'] / N, 1), medianDt=med(b['dt']))
        j = jdead[n]
        print(f"| {n} | {N} | {j['ownPct']} | {j['killerPct']} | {j['otherPct']} | {j['unfilledPct']} | {j['medianDt']} |")
    print('\n### (a4) Sprint vs AtomPush / AtomCrasher: races where both were adjacent to the square\n')
    print('| rival, window | races | Sprint won % | rival won % | third % | unfilled % | Sprint median ticks | rival median ticks | Sprint median child E | rival median child E |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    jpair = {}
    for k in sorted(pair, key=lambda k: (k[0].isdigit(), k)):
        p = pair[k]; N = p['n']
        jpair[k] = dict(races=N, sprintPct=round(100 * p['sprint'] / N, 1), rivalPct=round(100 * p['atom'] / N, 1), thirdPct=round(100 * p['other'] / N, 1),
                        unfilledPct=round(100 * p['unfilled'] / N, 1), sprintMedianDt=med(p['dtS']), rivalMedianDt=med(p['dtA']),
                        sprintMedianChildE=med(p['eS']), rivalMedianChildE=med(p['eA']),
                        sprintDtPct=dict(zip(lab(DT_BINS), bins(p['dtS'], DT_BINS))), rivalDtPct=dict(zip(lab(DT_BINS), bins(p['dtA'], DT_BINS))),
                        sprintChildEPct=dict(zip(lab(E_BINS), bins(p['eS'], E_BINS))), rivalChildEPct=dict(zip(lab(E_BINS), bins(p['eA'], E_BINS))))
        j = jpair[k]
        print(f"| {k.replace('|', ', ')} | {N} | {j['sprintPct']} | {j['rivalPct']} | {j['thirdPct']} | {j['unfilledPct']} | {j['sprintMedianDt']} | {j['rivalMedianDt']} | {j['sprintMedianChildE']} | {j['rivalMedianChildE']} |")
    print('\n### (b) Resting income: event-free cell-ticks that end +1\n')
    print('| cell | window | event-free cell-ticks | share of all cell-ticks % | +1 % | +1 % (start E < 50) | other delta % | median per-replay colony gain per tick | min-max |')
    print('|---|---|---|---|---|---|---|---|---|')
    jrest = {}
    for n in sorted(agg):
        jrest[n] = {}
        for w in range(3):
            a = agg[n][w]; free = a[0] + a[1] + a[2]
            if not free:
                continue
            v = inc[n][w]
            jrest[n][WN[w]] = dict(eventFree=free, eventFreeSharePct=round(100 * free / (free + a[5]), 1), plus1Pct=round(100 * a[1] / free, 2),
                                   plus1PctBelow50=round(100 * a[3] / a[4], 2) if a[4] else None, otherPct=round(100 * a[2] / free, 2),
                                   medianColonyGainPerTick=round(med(v), 2) if v else None, perReplayGainPerTick=[round(x, 2) for x in v],
                                   perReplayPlus1Pct=[round(100 * x, 2) for x in share_r[n][w]])
            j = jrest[n][WN[w]]
            print(f"| {n} | {WN[w]} | {free} | {j['eventFreeSharePct']} | {j['plus1Pct']} | {j['plus1PctBelow50']} | {j['otherPct']} | {j['medianColonyGainPerTick']} | {round(min(v), 1) if v else ''}-{round(max(v), 1) if v else ''} |")
    val = {rid: r['validation'] for rid, (r, _) in reps.items()}
    json.dump(dict(fillers=jfill, contested=jcont, byDeadCell=jdead, sprintVsAtom=jpair, validation=val), open(os.path.join(OUT, 'refill.json'), 'w'), indent=1)
    json.dump(dict(windows=WN, byCell=jrest), open(os.path.join(OUT, 'rest.json'), 'w'), indent=1)
    bad = {k: v for k, v in val.items() if v['kfMismatch'] or v['countMismatch'] or v['gridConflicts']}
    print(f"\nValidation: {len(val)} replays, keyframes checked {sum(v['kfChecked'] for v in val.values())}, problems: {bad or 'none'}")


if __name__ == '__main__':
    main()
