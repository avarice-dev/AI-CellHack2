"""One cell's ladder games tabulated from a saved match list, and names.json for mine.py and valtab.py.

Run: python -I tools/replay/tab.py --pull <pull> --cell <cell> [--matches FILE] [--rival <cell>] [--parts 2|3]
  --matches: the match-list JSON (schema: "Doing your own pull" in architecture/data-pulls.md); default the one
  data/<pull>/matches-*.json.  Games without --cell are left out of the tables but kept in names.json, so mine.py
  and valtab.py can name every replay of the pull.  --rival adds a same-game comparison with a second cell.
  --parts: the rating trend in halves (2) or thirds (3, default).
  Prints markdown; writes data/<pull>/names.json."""
import argparse, collections, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulls as P  # noqa: E402
ap = argparse.ArgumentParser(description="Tabulate one cell's ladder games from a saved match list.")
ap.add_argument('--pull', help='data folder name: writes data/<pull>/names.json')
ap.add_argument('--cell', help='the cell to tabulate')
ap.add_argument('--rival', help='a second cell for the same-game comparison (optional)')
ap.add_argument('--matches', help='match-list JSON (default: the one data/<pull>/matches-*.json)')
ap.add_argument('--parts', type=int, choices=(2, 3), default=3, help='rating trend in halves or thirds (default 3)')
A = ap.parse_args()
if not A.pull:
    P.no_pull('tab.py')
if not A.cell:
    sys.exit('tab.py: name the cell to tabulate with --cell <name>')
MF = A.matches
if not MF:
    lists = sorted(glob.glob(P.pull_dir(A.pull, 'matches-*.json')))
    if len(lists) != 1:
        sys.exit('no single match list in data/%s (found %d matches-*.json): give one with --matches, or save it '
                 'as data/%s/matches-<cell>-<date>.json (architecture/data-pulls.md)' % (A.pull, len(lists), A.pull))
    MF = lists[0]
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
    if ME not in col: continue          # a pull of several cells: names.json only
    me = col[ME]; pl = int(me['place']); places[pl] += 1; wins += pl == 1
    winner = [n for n, c in col.items() if c['place'] == '1'][0]
    if pl != 1: beat_by[winner] += 1
    for n in col:
        if n == ME: continue
        o = opp[n]; o[1] += 1; o[0] += pl == 1; o[2] += winner == n
    a, b = [int(x) for x in re.findall(r'\d+', me['rating'])[:2]]
    rows.append((m['id'], pl, me['pop'], winner, col[winner]['pop'], a, b))
    if RIVAL and RIVAL in col:
        h2h.append((m['id'], pl, int(col[RIVAL]['place']), winner, me['pop'], col[RIVAL]['pop']))
n = len(rows)
if not n:
    sys.exit('no games with %s in %s' % (ME, MF))
print(f'Games {n} (ids {rows[0][0]}-{rows[-1][0]}); won {wins} ({100*wins/n:.0f}%); places 1/2/3/4: '
      + '/'.join(str(places[i]) for i in (1, 2, 3, 4)))
peak = max(rows, key=lambda r: r[6])
print(f'Rating {rows[0][5]} -> {rows[-1][6]}; peak in window {peak[6]} after match {peak[0]}')
if A.parts == 2:
    k = (n + 1) // 2
    for half, rr in (('older', rows[:k]), ('newer', rows[k:])):
        if not rr: continue
        print(f'  {half} {len(rr)}: won {sum(r[1]==1 for r in rr)}/{len(rr)}, rating {rr[0][5]} -> {rr[-1][6]}')
else:
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
if RIVAL:
    hi = sum(c < s for _, c, s, *_ in h2h)
    print(f'\n{ME} vs {RIVAL} in the same game: {len(h2h)} games, {ME} placed higher in {hi}, {RIVAL} in {len(h2h) - hi}.')
    print(f'| Match | {ME} place | {RIVAL} place | Winner | {ME} pop | {RIVAL} pop |\n|---|---|---|---|---|---|')
    for r in h2h:
        print('| ' + ' | '.join(map(str, r)) + ' |')
os.makedirs(P.pull_dir(A.pull), exist_ok=True)
with open(P.pull_dir(A.pull, 'names.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump({str(m['id']): [nm(c['name']) for c in m['colonies']] for m in D}, f, ensure_ascii=False, indent=0)
