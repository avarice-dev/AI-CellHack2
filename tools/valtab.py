"""Validation table and start squares of decoded replays, offline (pure Python, no website).

Same statistics as the pull 2 in-page analysis (tools/pull2/analyze.js, report.py sec_val), so that sim/validate.py
can read pulls 3+ the same way as data/pull2/validation-table.md:
  pop at ticks 50, 100, 200, 500, 1000 (tick record), end (last tick record), mean energy of the colony's cells at
  keyframes 200 and 1000 (None when it has no cells or no such keyframe), feeds per enemy eat (None when no enemy
  eats), freeze tick (earliest t with every colony's later population within 5% of its pop at t),
  start square of each colony (its first cell in keyframe 0).

Usage: CH_PULL=pull3 python -I tools/valtab.py [replay ids...]
  reads data/<pull>/replays/<id>.chr2.gz and data/<pull>/names.json (or summaries/<id>.json for pull 2),
  writes data/<pull>/validation-table.md and data/<pull>/starts.json (all replays of the pull, sorted by id).
  With ids given, prints those rows only and writes nothing (used to check pull 2 against its table).
Runs at below-normal priority on Windows. Single process.
"""
import ctypes, gzip, json, os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PULL = os.environ.get('CH_PULL', 'pull3')
KEEP = (50, 100, 200, 500, 1000)


def below_normal():
    if os.name == 'nt':
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL_PRIORITY_CLASS


def nm(s):
    return re.sub(r'^\W+\s*', '', s).strip()


def freeze_tick(pops):
    """analyze.js: scan back from the last tick while every colony's later pops stay within 5% of pop(t)."""
    T = len(pops)
    mx, mn = [0] * 4, [10 ** 9] * 4
    best = T
    for t in range(T - 1, -1, -1):
        ok = True
        for c in range(4):
            p = pops[t][c]
            mx[c] = max(mx[c], p)
            mn[c] = min(mn[c], p)
            if not (mx[c] <= p * 1.05 and mn[c] >= p * 0.95):
                ok = False
        if not ok:
            break
        best = t
    return best


def decode(raw):
    """-> dict(pops per tick, starts per colony (x, y) or None, meanE {200, 1000: [4]}, feeds [4], eats_enemy [4])."""
    if raw[:4] != b'CHR2':
        raise ValueError('not a CHR2 replay')
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    if version != 4:
        raise ValueError('version %d: only u8-energy format 4 is handled' % version)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2, U16x4 = struct.Struct('<I'), struct.Struct('<II'), struct.Struct('<HHHH')
    BIRTH = struct.Struct('<IBHHB')
    colOf, pops, meanE, starts = {}, [], {}, None
    feeds, eats = [0] * 4, [0] * 4
    n_raw = len(raw)
    while p < n_raw:
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8
            per = [[] for _ in range(4)]
            first = [None] * 4
            for _ in range(n):
                cid, c, x, y, e = BIRTH.unpack_from(raw, p); p += 10
                per[c].append(e)
                if first[c] is None:
                    first[c] = (x, y)
                if starts is None:
                    colOf[cid] = c
            if starts is None:
                starts = first
            if tick in (200, 1000):
                meanE[tick] = [round(sum(a) / len(a), 3) if a else None for a in per]
        elif rt == 1:
            pops.append(list(U16x4.unpack_from(raw, p + 4))); p += 12
            nev = U32.unpack_from(raw, p)[0]; p += 4
            for _ in range(nev):
                k = raw[p]
                if k == 5:
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    feeds[colOf[a]] += 1
                elif k == 4:
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if colOf[a] != colOf[b]:
                        eats[colOf[a]] += 1
                elif k == 1:
                    cid, c = BIRTH.unpack_from(raw, p + 1)[:2]; p += 11
                    colOf[cid] = c
                elif k == 2:
                    p += 9
                elif k == 3:
                    p += 5
                else:
                    raise ValueError('bad event %d' % k)
            n = U32.unpack_from(raw, p)[0]; p += 4 + n
        elif rt == 3:
            p += 5 + 4 + 8
        else:
            raise ValueError('record type %d not handled' % rt)
    return dict(pops=pops, starts=starts, meanE=meanE, feeds=feeds, eats_enemy=eats)


def js(v):
    """Number text as the JS report prints it (5.0 -> 5)."""
    return '%d' % v if isinstance(v, float) and v.is_integer() else str(v)


def rows(rid, names, d):
    pops = d['pops']
    T = len(pops)
    fz = freeze_tick(pops)
    out = []
    for c in range(4):
        g = lambda t: pops[t][c] if t < T else '-'
        e = lambda t: d['meanE'][t][c] if t in d['meanE'] else None
        fpe = round(d['feeds'][c] / d['eats_enemy'][c], 3) if d['eats_enemy'][c] else None
        out.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            rid, names[c], g(50), g(100), g(200), g(500), g(1000), pops[T - 1][c], js(e(200)), js(e(1000)), js(fpe),
            fz))
    return out


def load_names(rid):
    sp = os.path.join(ROOT, 'data', PULL, 'summaries', '%s.json' % rid)
    if os.path.exists(sp):
        names = json.load(open(sp, encoding='utf-8'))['names']
    else:
        names = json.load(open(os.path.join(ROOT, 'data', PULL, 'names.json'), encoding='utf-8'))[str(rid)]
    return [nm(n) for n in names]


def main():
    below_normal()
    rep = os.path.join(ROOT, 'data', PULL, 'replays')
    ids = sys.argv[1:] or sorted(f.split('.')[0] for f in os.listdir(rep) if f.endswith('.chr2.gz'))
    table, starts = [], {}
    for rid in ids:
        d = decode(gzip.decompress(open(os.path.join(rep, '%s.chr2.gz' % rid), 'rb').read()))
        names = load_names(rid)
        r = rows(rid, names, d)
        table += r
        starts[rid] = [[names[c]] + list(d['starts'][c]) for c in range(4)]
        if sys.argv[1:]:
            print('\n'.join(r), flush=True)
    if sys.argv[1:]:
        return
    with open(os.path.join(ROOT, 'data', PULL, 'validation-table.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('### val (%s, tools/valtab.py)\n' % PULL)
        f.write('| match | colony | pop t50 | t100 | t200 | t500 | t1000 | end | E t200 | E t1000 | feeds/eat | freeze |\n')
        f.write('|---|---|---|---|---|---|---|---|---|---|---|---|\n')
        f.write('\n'.join(table) + '\n')
    with open(os.path.join(ROOT, 'data', PULL, 'starts.json'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('{\n' + ',\n'.join('"%s": %s' % (k, json.dumps(v)) for k, v in starts.items()) + '\n}\n')
    print('%s: %d matches' % (PULL, len(ids)))


if __name__ == '__main__':
    main()
