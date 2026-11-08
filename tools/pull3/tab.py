"""Pull 3: Scourge's recent ladder games tabulated from data/pull3/matches-scourge-2026-11-08.json.
Run: python -I tools/pull3/tab.py   (prints markdown; writes data/pull3/names.json for mine.py)"""
import json, os, re, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = json.load(open(os.path.join(ROOT, 'data', 'pull3', 'matches-scourge-2026-11-08.json'), encoding='utf-8'))['matches']
nm = lambda s: re.sub(r'^\W+\s*', '', s).strip()
ME = 'Scourge'
D = sorted(D, key=lambda m: m['id'])
places = collections.Counter(); wins = 0
opp = collections.defaultdict(lambda: [0, 0, 0])        # wins, games, rival won
beat_by = collections.Counter(); rows = []
for m in D:
    col = {nm(c['name']): c for c in m['colonies']}
    me = col[ME]; pl = int(me['place']); places[pl] += 1; wins += pl == 1
    winner = [n for n, c in col.items() if c['place'] == '1'][0]
    if pl != 1: beat_by[winner] += 1
    for n in col:
        if n == ME: continue
        o = opp[n]; o[1] += 1; o[0] += pl == 1; o[2] += winner == n
    a, b = [int(x) for x in re.findall(r'\d+', me['rating'])[:2]]
    rows.append((m['id'], pl, me['pop'], winner, col[winner]['pop'], a, b))
n = len(D)
print(f'Games {n} (ids {D[0]["id"]}-{D[-1]["id"]}); won {wins} ({100*wins/n:.0f}%); places 1/2/3/4: '
      + '/'.join(str(places[i]) for i in (1, 2, 3, 4)))
peak = max(rows, key=lambda r: r[6])
print(f'Rating {rows[0][5]} -> {rows[-1][6]}; peak in window {peak[6]} after match {peak[0]}')
for half, rr in (('older 50', rows[:50]), ('newer 50', rows[50:])):
    print(f'  {half}: won {sum(r[1]==1 for r in rr)}/{len(rr)}, rating {rr[0][5]} -> {rr[-1][6]}')
print('\n| Opponent | Scourge wins / games | Opponent won |\n|---|---|---|')
for k, (w, g, r) in sorted(opp.items(), key=lambda kv: -kv[1][1]):
    print(f'| {k} | {w}/{g} | {r} |')
print('\nLosses by winner:', ', '.join(f'{k} {v}' for k, v in beat_by.most_common()))
print('\n| Match | Scourge place | Scourge pop | Winner | Winner pop |\n|---|---|---|---|---|')
for r in rows:
    if r[1] != 1: print(f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |')
json.dump({str(m['id']): [nm(c['name']) for c in m['colonies']] for m in D},
          open(os.path.join(ROOT, 'data', 'pull3', 'names.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
