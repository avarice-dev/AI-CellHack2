"""Scratch: run a per-replay scratch script (args: <replay dir> <names.json> <out.csv> [id ...]) over many replays,
at most N processes at once, one replay per process call batch of B, idle priority.  Writes <prefix>-<pull>-<k>.csv
and concatenates them into <prefix>.csv at the end.
Usage: python par.py <repo> <script.py> <prefix> <N> <B> pull9[:id,id] pull8 ...
"""
import csv
import os
import subprocess
import sys
import time

repo, script, prefix, N, B = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
jobs = []
for spec in sys.argv[6:]:
    pull, _, ids = spec.partition(':')
    ids = ids.split(',') if ids else sorted(f.split('.')[0] for f in os.listdir(os.path.join(repo, 'data', pull, 'replays')))
    for k in range(0, len(ids), B):
        jobs.append((pull, k // B, ids[k:k + B]))
IDLE = 0x00000040
running, outs = [], []
while jobs or running:
    running = [(p, o) for p, o in running if p.poll() is None]
    while jobs and len(running) < N:
        pull, k, ids = jobs.pop(0)
        out = '%s-%s-%d.csv' % (prefix, pull, k)
        log = open(out[:-4] + '.log', 'w')
        p = subprocess.Popen([sys.executable, '-I', script, os.path.join(repo, 'data', pull, 'replays'),
                              os.path.join(repo, 'data', pull, 'names.json'), out] + ids,
                             stdout=log, stderr=subprocess.STDOUT, creationflags=IDLE)
        running.append((p, out))
        outs.append(out)
    time.sleep(2)
rows, fields = [], None
for o in outs:
    if not os.path.exists(o):
        print('missing', o)
        continue
    r = list(csv.DictReader(open(o, encoding='utf-8')))
    if r:
        fields = fields or list(r[0])
        rows += r
with open(prefix + '.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print('wrote', prefix + '.csv', len(rows), 'rows from', len(outs), 'parts')
