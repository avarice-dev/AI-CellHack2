"""Scratch: pool bites.py CSVs per cell name and window.  Usage: python bites_sum.py <out.txt> <csv> [...]"""
import csv, sys, collections
rows = []
for f in sys.argv[2:]:
    rows += list(csv.DictReader(open(f, encoding='utf-8')))
def label(n, rid):
    """The site names every Bane version 'Bane': label by match id."""
    if n != 'Bane':
        return n
    rid = int(rid)
    return 'Bane v1' if rid < 124690 else 'Bane v2.0' if rid < 126000 else 'Bane v2.1' if rid < 127810 else 'Bane v2.2'
c = collections.defaultdict(collections.Counter)
games = collections.defaultdict(set)
for r in rows:
    c[(label(r['name'], r['replay']), r['window'])][r['measure']] += int(r['n'])
    games[label(r['name'], r['replay'])].add(r['replay'])
out = open(sys.argv[1], 'w', encoding='utf-8')
P = lambda *a: print(*a, file=out)
P('# Bite side per cell, pooled. stun% = own cells bitten before their turn per contact cell-tick; friendly = bites on own')
P('# cells per 100 enemy bites; chain = mean consecutive-tick bites on one target; kill->next: killer action next tick (%);')
P('# freed->: who filled the square freed by the kill on the next tick (%); low2/low4 = share of bites suffered at energy <=2 / <=4.')
P('# windows: a t<60, b 60-100, c 100-300, d 300+ (chains are pooled over the game in window all)')
for n in sorted(games, key=lambda n: -len(games[n])):
    if len(games[n]) < 3:
        continue
    ch = c[(n, 'all')]
    chains = sum(c[(n, w)]['chains'] for w in 'abcd') + ch['chains']
    clen = sum(c[(n, w)]['chain_len'] for w in 'abcd') + ch['chain_len']
    P('\n%s (%d games) mean chain %.1f' % (n, len(games[n]), clen / chains if chains else 0))
    for w in 'abcd':
        x = c[(n, w)]
        if not x['contact']:
            continue
        ak = x['after_kill_n'] or 1
        fr = x['freed_next_own'] + x['freed_next_other'] + x['freed_next_nobody'] or 1
        bt = x['bitten_total'] or 1
        P('  %s contact %7d stun %5.1f%% bites %7d friendly %4.1f kills %6d | kill->next take %4.1f eat %4.1f none %4.1f stunned %4.1f split %4.1f move %4.1f | freed-> own %4.1f other %4.1f nobody %4.1f | low2 %4.1f low4 %4.1f' % (
            w, x['contact'], 100 * x['stunned'] / x['contact'], x['eats_enemy'], 100 * x['eats_friend'] / (x['eats_enemy'] or 1), x['kills'],
            100 * x['after_kill_take'] / ak, 100 * x['after_kill_eat'] / ak, 100 * x['after_kill_none'] / ak, 100 * x['after_kill_bitten'] / ak,
            100 * x['after_kill_split'] / ak, 100 * x['after_kill_move'] / ak,
            100 * x['freed_next_own'] / fr, 100 * x['freed_next_other'] / fr, 100 * x['freed_next_nobody'] / fr,
            100 * x['bitten_le2'] / bt, 100 * x['bitten_le4'] / bt))
out.close()
