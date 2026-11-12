"""Scratch: front.py measures (full columns, tmin 0) on listed replays of several pulls, in parallel, one CSV.
Usage: python front_many.py <repo> <out.csv> <procs> pull8:id,id,... pull9:id,... [...]   (pullN:all = every replay)
Runs at below-normal priority.
"""
import csv
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import front as F                                     # noqa: E402  (the scratch front.py beside this file)


def one(job):
    repo, pull, rid = job
    rdir = os.path.join(repo, 'data', pull, 'replays')
    f = next(x for x in os.listdir(rdir) if x.split('.')[0] == rid)
    st, ncol, first, bites, took_from = F.front(os.path.join(rdir, f), 0)
    names = json.load(open(os.path.join(repo, 'data', pull, 'names.json'), encoding='utf-8'))
    nm = names.get(rid, [])
    rows = []
    for c in range(ncol):
        s = st[c]
        others = [o for o in range(ncol) if o != c]
        ct, tk = max(s['contact'], 1), max(s['took'], 1)
        name = nm[c] if c < len(nm) else 'colony %d' % c
        name = name.split(' ', 1)[-1] if not name[:1].isalnum() else name
        row = dict(pull=pull, replay=rid, name=name, colony=c, contact=s['contact'], took=s['took'],
                   took_e=round(s['took_e'] / tk, 2), took_e2=round(100 * s['took_e2'] / tk, 1),
                   took_e4=round(100 * s['took_e4'] / tk, 1), took_dead5=round(100 * s['took_dead5'] / tk, 1))
        for w in ('eat', 'feed', 'split', 'move', 'bitten', 'none'):
            row['c_' + w] = round(100 * s['c_' + w] / ct, 1)
        row['none_lo'] = round(100 * s['none_lo'] / ct, 1)
        row['none_hi'] = round(100 * s['none_hi'] / ct, 1)
        for kind in ('fr', 'on'):
            n = max(s[kind], 1)
            row[kind] = s[kind]
            for w in ('eat', 'bitten', 'none'):
                row[kind + '_' + w] = round(100 * s[kind + '_' + w] / n, 1)
        for w in ('a', 'b', 'c'):
            n = max(s['ct_' + w], 1)
            row['ct_' + w] = s['ct_' + w]
            row['ctw_' + w] = round(100 * s['ctw_' + w] / n, 1)
            row['ctl_' + w] = round(100 * s['ctl_' + w] / n, 1)
        row['first'] = json.dumps({o: first.get((min(c, o), max(c, o)), (-1, []))[0] for o in others})
        row['closed'] = json.dumps({o: c in first.get((min(c, o), max(c, o)), (-1, []))[1] for o in others})
        row['bites_on'] = json.dumps({o: bites[(c, o)] for o in others})
        row['bitten_by'] = json.dumps({o: bites[(o, c)] for o in others})
        row['took_from'] = json.dumps({o: took_from[(c, o)] for o in others})
        rows.append(row)
    return rows


def low():
    try:
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass


if __name__ == '__main__':
    repo, out, procs = sys.argv[1], sys.argv[2], int(sys.argv[3])
    jobs = []
    for spec in sys.argv[4:]:
        pull, ids = spec.split(':', 1)
        if ids == 'all':
            ids = sorted(x.split('.')[0] for x in os.listdir(os.path.join(repo, 'data', pull, 'replays')))
        else:
            ids = ids.split(',')
        jobs += [(repo, pull, i) for i in ids if i]
    low()
    rows = []
    with Pool(procs, initializer=low) as pool:
        for rs in pool.imap_unordered(one, jobs):
            rows += rs
            print(rs[0]['pull'], rs[0]['replay'], 'done', flush=True)
    rows.sort(key=lambda r: (r['replay'], r['colony']))
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print('wrote', out, len(rows))
