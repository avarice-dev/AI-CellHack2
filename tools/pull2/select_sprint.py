"""Candidate table for direction-profile replays: Sprint matches with Sprint's survival. python -I tools/pull2/select_sprint.py
History: reproduces our pull 2 report (data/ladder-data-2-2026-11-08.md); reads only data/pull2 in the pull 2 formats."""
import json, re
P = json.load(open('data/pull2/sprint-match-pages.json', encoding='utf-8'))['pages']
def nm(s): return re.sub(r'^\W+\s*', '', s).strip()
rows = []
for id_, m in P.items():
    cs = [(nm(r[1]), r[2], int(r[3]), int(r[4]), int(r[5])) for r in m['rows']]
    sp = [c for c in cs if c[0] == 'Sprint'][0]
    rows.append((int(id_), sp, cs))
rows.sort(key=lambda r: -(r[1][4] if r[1][3] == 0 else r[1][3] + 5000))   # survivors first, then by peak
for id_, sp, cs in rows[:60]:
    print(id_, 'Sprint pl%d fin%d peak%d |' % (sp[2], sp[3], sp[4]), ' '.join('%s:%d/%d' % (c[0], c[2], c[3]) for c in cs if c[0] != 'Sprint'))
