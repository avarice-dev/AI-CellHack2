"""Late front movement and freeze ticks per replay. python -I tools/pull2/late.py
History: reproduces our pull 2 report (data/ladder-data-2-2026-11-08.md); reads only data/pull2 in the pull 2 formats."""
import json, glob, re
nm = lambda s: re.sub(r'^\W+\s*', '', s).strip()
rows = []
for f in sorted(glob.glob('data/pull2/summaries/[0-9]*.json')):
    d = json.load(open(f, encoding='utf-8')); cs = [nm(r['cell']) for r in d['facts']['rows']]
    best = (0, None)
    for c in range(4):
        p = d['pop10'][c]
        if len(p) <= 50: continue
        a, b = p[50], d['popFinal'][c]
        mv = abs(b - a)
        if mv > best[0]: best = (mv, '%s %d->%d' % (cs[c], a, b))
    mx = max(max(d['pop10'][c]) for c in range(4))
    rows.append((best[0], d['id'], best[1], d['freezeTick'], d['ticksInReplay'], d['end']['reason']))
rows.sort(reverse=True)
print('largest change in a colony population between t500 and the end (id, colony pop t500->end, freeze tick, ticks run, end reason):')
for r in rows[:12]: print(' ', r[1], r[2], 'change', r[0], 'freeze', r[3], 'ticks', r[4], 'reason', r[5])
fz = sorted(r[3] for r in rows)
print('freeze tick: min %d median %d max %d; <=500: %d of %d' % (fz[0], fz[len(fz)//2], fz[-1], sum(1 for x in fz if x <= 500), len(fz)))
