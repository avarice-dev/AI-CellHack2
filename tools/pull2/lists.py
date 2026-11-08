"""Win rates and head-to-heads from data/pull2/matches-*.json (+ first pull baseline, hard-coded from
data/ladder-data-2026-11-08.md section 2). Run: python -I tools/pull2/lists.py"""
import json, glob, re, itertools, collections, sys
f = sorted(glob.glob('data/pull2/matches-*.json'))[0]
D = json.load(open(f, encoding='utf-8'))['matches']
def nm(s): return re.sub(r'^\W+\s*', '', s).strip()
OLD = {'AtomPush':(61,79),'AtomCrasher':(62,83),'Bouncer':(43,82),'rooby':(37,71),'Brawler v2':(40,77),'Sprint':(12,24),
 'Noob+':(33,76),'Brawler':(31,75),'Aegis':(27,73),'Noob++':(18,72),'Noob':(16,83),'gemAlert_v4':(8,75),'Hunter':(7,79),
 'squirtle':(4,80),'zergling':(1,81),'gemAlert_v3':(1,81),'Medic':(1,83),'Bulwark':(0,79),'choochoo':(0,81),'Walker':(0,80),'Random':(0,85)}
g = collections.Counter(); w = collections.Counter(); h2h = collections.defaultdict(lambda: [0,0,0])
ham = {'AtomPush','AtomCrasher'}; ups = []
for m in D:
    cs = [nm(c) for c in m['cells']]; win = nm(m['winner']) if m['winner'] else None
    for c in set(cs):
        g[c] += 1
        if c == win: w[c] += 1
    for a, b in itertools.combinations(sorted(set(cs)), 2):
        k = (a, b); h2h[k][0] += (win == a); h2h[k][1] += (win == b); h2h[k][2] += (win not in (a, b))
    if ham & set(cs) and win not in ham: ups.append((m['id'], win, cs))
out = {'matches': len(D), 'id_range': [D[0]['id'], D[-1]['id']], 'cells': {}}
print('matches', len(D), D[0]['id'], D[-1]['id'])
print('%-12s %9s %9s %11s' % ('cell','new w/g','old w/g','all w/g %'))
for c in sorted(g, key=lambda c: -(w[c]+OLD.get(c,(0,0))[0])/(g[c]+OLD.get(c,(0,1))[1])):
    ow, og = OLD.get(c, (0, 0)); aw, ag = w[c]+ow, g[c]+og
    out['cells'][c] = {'new': [w[c], g[c]], 'old': [ow, og], 'all': [aw, ag]}
    print('%-12s %4d/%-4d %4d/%-4d %4d/%-4d %5.1f%%' % (c, w[c], g[c], ow, og, aw, ag, 100*aw/ag))
print('\nHead-to-head (new only; a wins / b wins / other), pairs with n>=12:')
for (a, b), (x, y, z) in sorted(h2h.items(), key=lambda kv: -sum(kv[1])):
    if sum((x, y, z)) >= 12 and not ({a, b} & {'Random','Walker','Medic','choochoo','Hunter'}):
        print('  %s vs %s: %d/%d/%d (n%d)' % (a, b, x, y, z, x+y+z))
print('\nHammerSpb upsets (new): %d of %d matches containing them' % (len(ups), sum(1 for m in D if ham & {nm(c) for c in m['cells']})))
print(collections.Counter(u[1] for u in ups).most_common())
json.dump({'summary': out, 'h2h': {a+' | '+b: v for (a, b), v in h2h.items()}, 'hammer_upsets': ups}, open('data/pull2/winrates.json', 'w', encoding='utf-8', newline='\n'), indent=1)
