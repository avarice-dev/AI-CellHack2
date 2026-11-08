"""Pull 4: Contagion's ladder games tabulated from data/pull4/matches-contagion-2026-11-08.json (same as pull 3's tab.py,
plus a rating trend by thirds and a Contagion-vs-Scourge head-to-head).
Run: python -I tools/pull4/tab.py [--pull P] [--cell NAME] [--rival NAME] [--matches FILE]
  (prints markdown; writes data/<pull>/names.json for mine.py and valtab.py;
  defaults: pull4, Contagion, Scourge, the pull 4 match list)"""
import argparse, json, os, re, collections, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser(description="Tabulate one cell's ladder games from a saved match list.")
ap.add_argument('--pull', default='pull4', help='data folder name: writes data/<pull>/names.json (default pull4)')
ap.add_argument('--cell', default='Contagion', help='the cell to tabulate (default Contagion)')
ap.add_argument('--rival', default='Scourge', help='cell for the same-game comparison (default Scourge)')
ap.add_argument('--matches', help='match-list JSON (default data/pull4/matches-contagion-2026-11-08.json)')
A = ap.parse_args()
MF = A.matches or os.path.join(ROOT, 'data', 'pull4', 'matches-contagion-2026-11-08.json')
if not os.path.exists(MF):
    sys.exit('match list %s not found: run a pull first (architecture/data-pulls.md)' % MF)
D = json.load(open(MF, encoding='utf-8'))['matches']
nm = lambda s: re.sub(r'^\W+\s*', '', s).strip()
ME, RIVAL = A.cell, A.rival
D = sorted(D, key=lambda m: m['id'])
places = collections.Counter(); wins = 0
opp = collections.defaultdict(lambda: [0, 0, 0])        # wins, games, rival won
beat_by = collections.Counter(); rows = []; h2h = []
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
    if RIVAL in col:
        h2h.append((m['id'], pl, int(col[RIVAL]['place']), winner, me['pop'], col[RIVAL]['pop']))
n = len(D)
print(f'Games {n} (ids {D[0]["id"]}-{D[-1]["id"]}); won {wins} ({100*wins/n:.0f}%); places 1/2/3/4: '
      + '/'.join(str(places[i]) for i in (1, 2, 3, 4)))
peak = max(rows, key=lambda r: r[6])
print(f'Rating {rows[0][5]} -> {rows[-1][6]}; peak in window {peak[6]} after match {peak[0]}')
k = n // 3
for part, rr in (('oldest third', rows[:k]), ('middle third', rows[k:2 * k]), ('newest third', rows[2 * k:])):
    if not rr: continue
    print(f'  {part} ({rr[0][0]}-{rr[-1][0]}): won {sum(r[1]==1 for r in rr)}/{len(rr)}, rating {rr[0][5]} -> {rr[-1][6]}')
print(f'\n| Opponent | {ME} wins / games | Opponent won |\n|---|---|---|')
for kk, (w, g, r) in sorted(opp.items(), key=lambda kv: -kv[1][1]):
    print(f'| {kk} | {w}/{g} | {r} |')
print('\nLosses by winner:', ', '.join(f'{kk} {v}' for kk, v in beat_by.most_common()))
print(f'\n| Match | {ME} place | {ME} pop | Winner | Winner pop |\n|---|---|---|---|---|')
for r in rows:
    if r[1] != 1: print(f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |')
hi = sum(c < s for _, c, s, *_ in h2h)
print(f'\n{ME} vs {RIVAL} in the same game: {len(h2h)} games, {ME} placed higher in {hi}, {RIVAL} in {len(h2h) - hi}.')
print(f'| Match | {ME} place | {RIVAL} place | Winner | {ME} pop | {RIVAL} pop |\n|---|---|---|---|---|---|')
for r in h2h:
    print('| ' + ' | '.join(map(str, r)) + ' |')
os.makedirs(os.path.join(ROOT, 'data', A.pull), exist_ok=True)
with open(os.path.join(ROOT, 'data', A.pull, 'names.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump({str(m['id']): [nm(c['name']) for c in m['colonies']] for m in D}, f, ensure_ascii=False, indent=0)
