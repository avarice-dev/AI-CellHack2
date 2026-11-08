"""Pull 3: Scourge's recent ladder games tabulated from data/pull3/matches-scourge-2026-11-08.json.
Run: python -I tools/pull3/tab.py [--pull P] [--cell NAME] [--matches FILE]
  (prints markdown; writes data/<pull>/names.json for mine.py and valtab.py;
  defaults: pull3, Scourge, the pull 3 match list)"""
import argparse, json, os, re, collections, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser(description="Tabulate one cell's ladder games from a saved match list.")
ap.add_argument('--pull', default='pull3', help='data folder name: writes data/<pull>/names.json (default pull3)')
ap.add_argument('--cell', default='Scourge', help='the cell to tabulate (default Scourge)')
ap.add_argument('--matches', help='match-list JSON (default data/pull3/matches-scourge-2026-11-08.json)')
A = ap.parse_args()
MF = A.matches or os.path.join(ROOT, 'data', 'pull3', 'matches-scourge-2026-11-08.json')
if not os.path.exists(MF):
    sys.exit('match list %s not found: run a pull first (architecture/data-pulls.md)' % MF)
D = json.load(open(MF, encoding='utf-8'))['matches']
nm = lambda s: re.sub(r'^\W+\s*', '', s).strip()
ME = A.cell
D = sorted(D, key=lambda m: m['id'])
places = collections.Counter(); wins = 0
opp = collections.defaultdict(lambda: [0, 0, 0])        # wins, games, rival won
beat_by = collections.Counter(); rows = []
for m in D:
    col = {nm(c['name']): c for c in m['colonies']}
    if ME not in col: continue          # a pull of several cells: names.json only
    me = col[ME]; pl = int(me['place']); places[pl] += 1; wins += pl == 1
    winner = [n for n, c in col.items() if c['place'] == '1'][0]
    if pl != 1: beat_by[winner] += 1
    for n in col:
        if n == ME: continue
        o = opp[n]; o[1] += 1; o[0] += pl == 1; o[2] += winner == n
    a, b = [int(x) for x in re.findall(r'\d+', me['rating'])[:2]]
    rows.append((m['id'], pl, me['pop'], winner, col[winner]['pop'], a, b))
n = len(rows)
if not n:
    sys.exit('no games with %s in %s' % (ME, MF))
print(f'Games {n} (ids {rows[0][0]}-{rows[-1][0]}); won {wins} ({100*wins/n:.0f}%); places 1/2/3/4: '
      + '/'.join(str(places[i]) for i in (1, 2, 3, 4)))
peak = max(rows, key=lambda r: r[6])
print(f'Rating {rows[0][5]} -> {rows[-1][6]}; peak in window {peak[6]} after match {peak[0]}')
for half, rr in (('older 50', rows[:50]), ('newer 50', rows[50:])):
    if not rr: continue
    print(f'  {half}: won {sum(r[1]==1 for r in rr)}/{len(rr)}, rating {rr[0][5]} -> {rr[-1][6]}')
print(f'\n| Opponent | {ME} wins / games | Opponent won |\n|---|---|---|')
for k, (w, g, r) in sorted(opp.items(), key=lambda kv: -kv[1][1]):
    print(f'| {k} | {w}/{g} | {r} |')
print('\nLosses by winner:', ', '.join(f'{k} {v}' for k, v in beat_by.most_common()))
print(f'\n| Match | {ME} place | {ME} pop | Winner | Winner pop |\n|---|---|---|---|---|')
for r in rows:
    if r[1] != 1: print(f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |')
os.makedirs(os.path.join(ROOT, 'data', A.pull), exist_ok=True)
with open(os.path.join(ROOT, 'data', A.pull, 'names.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump({str(m['id']): [nm(c['name']) for c in m['colonies']] for m in D}, f, ensure_ascii=False, indent=0)
