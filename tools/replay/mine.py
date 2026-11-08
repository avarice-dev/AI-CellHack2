"""Offline replay mining of one data pull (no website, no Node).

A pure-Python port of the site's CHR2 decoder (CellHackViewer.decode + State.apply in the site's /static/viewer.js),
streamed one tick at a time, with two analyses:

(a) Refill race: every death frees a square; record who next occupies it (birth or move), how many ticks later, and the
    occupant's energy (child energy for a birth, mover's start-of-tick energy for a move). Also the colonies that had a
    cell orthogonally adjacent to the square at the moment of death (the contenders) and the colony of the last eater
    of the dead cell (the killer). One CSV row per death: data/<pull>/mining/races/<id>.csv.gz
(b) Resting income: for every cell-tick with no event on the cell (not eater, target, feeder, receiver, mover, newborn),
    the energy delta end-of-tick minus start-of-tick, counted per colony, time window and start energy.
    Saved in data/<pull>/mining/<id>.json.

Validation as in analyze.js: start-of-tick state must equal each keyframe (ids, colony, x, y, energy, order) and the
per-tick energies count must equal the modelled cell count.

Usage: python -I tools/replay/mine.py --pull <pull> [replay ids...]
  (default: every data/<pull>/replays/*.chr2.gz without output; colony names from data/<pull>/names.json, written by
  tab.py, or from data/<pull>/summaries/<id>.json, the pull 2 format)
Runs at below-normal priority on Windows. Single process.
"""
import ctypes, gzip, json, os, struct, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulls as P  # noqa: E402
PULL = REP = SUM = OUT = None   # set by main() from --pull
WINDOWS = (500, 1000)          # window 0: t < 500, 1: 500 <= t < 1000, 2: t >= 1000


def win(t):
    return 0 if t < WINDOWS[0] else 1 if t < WINDOWS[1] else 2


def below_normal():
    if os.name == 'nt':
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL_PRIORITY_CLASS


def mine(rid):
    raw = gzip.decompress(open(os.path.join(REP, f'{rid}.chr2.gz'), 'rb').read())
    if raw[:4] != b'CHR2':
        raise ValueError('not a CHR2 replay')
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    if version != 4:
        raise ValueError(f'version {version}: only u8-energy format 4 is handled')
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2, U16x4 = struct.Struct('<I'), struct.Struct('<II'), struct.Struct('<HHHH')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')

    ids, cols, prev = [], [], []           # order of cells at start of tick (viewer State order) and energies
    colOf, sqOf = {}, {}                   # id -> colony, id -> square
    grid = [0] * (W * H)                   # id + 1, or 0
    lastEater = {}                         # target id -> colony of its last eater
    pending = {}                           # square -> [tDeath, deadCol, killerCol, contMask, deadId]
    races = []                             # rows
    R = [0] * (4 * 3 * 256 * 3)            # (c, window, startE, code) code 0: delta 0, 1: +1, 2: other
    other = {}                             # (c, w, delta) -> n for code 2
    touchedN = [0] * 12                    # cell-ticks with an event, per (c, w)
    val = dict(kfChecked=0, kfMismatch=0, countMismatch=0, ticks=0, events=0, gridConflicts=0)
    kfs = {}
    pops = []                              # per tick: colony populations from the tick record
    early = {}                             # (colony, kind 'b' birth child energy / 'm' move, value) -> n, t < 200
    loaded = False
    cur = 0
    end = None
    n_raw = len(raw)

    def check_kf(t):
        cells = kfs.pop(t)
        val['kfChecked'] += 1
        bad = len(cells) != len(ids)
        if not bad:
            for (cid, c, x, y, e), a, b, q in zip(cells, ids, cols, prev):
                if cid != a or c != b or e != q or sqOf.get(cid) != y * W + x:
                    bad = True
                    break
        if bad:
            val['kfMismatch'] += 1

    while p < n_raw:
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8
            cells = []
            for _ in range(n):
                cid, c, x, y, e = BIRTH.unpack_from(raw, p); p += 10
                cells.append((cid, c, x, y, e))
            if not loaded:
                for cid, c, x, y, e in cells:
                    ids.append(cid); cols.append(c); prev.append(e); colOf[cid] = c
                    sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                loaded = True
            else:
                kfs[tick] = cells
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]
            pops.append(list(U16x4.unpack_from(raw, p + 4))); p += 4 + 8
            if t in kfs:
                check_kf(t)
            nev = U32.unpack_from(raw, p)[0]; p += 4
            val['ticks'] += 1; val['events'] += nev
            touched = set(); dead = set(); births = []
            for _ in range(nev):
                k = raw[p]
                if k == 5:
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    touched.add(a); touched.add(b)
                elif k == 4:
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    touched.add(a); touched.add(b); lastEater[b] = colOf[a]
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    s = y * W + x
                    colOf[cid] = c; sqOf[cid] = s
                    if grid[s]:
                        val['gridConflicts'] += 1
                    grid[s] = cid + 1
                    touched.add(cid); births.append(cid)
                    if t < 200:
                        kk = f'{c},b,{e}'; early[kk] = early.get(kk, 0) + 1
                    pr = pending.pop(s, None)
                    if pr is not None:
                        races.append((pr[0], pr[1], pr[2], pr[3], c, t - pr[0], 1, e))
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]; s = y * W + x
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    if grid[s]:
                        val['gridConflicts'] += 1
                    grid[s] = cid + 1; sqOf[cid] = s
                    touched.add(cid)
                    if t < 200:
                        kk = f'{colOf[cid]},m,0'; early[kk] = early.get(kk, 0) + 1
                    pr = pending.pop(s, None)
                    if pr is not None:
                        try:
                            e = prev[ids.index(cid)]
                        except ValueError:
                            e = -1
                        races.append((pr[0], pr[1], pr[2], pr[3], colOf[cid], t - pr[0], 2, e))
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    touched.add(cid); dead.add(cid)
                    s = sqOf[cid]; dc = colOf[cid]
                    if grid[s] == cid + 1:
                        grid[s] = 0
                    x, y = s % W, s // W
                    mask = 0
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < W and 0 <= ny < H:
                            g = grid[ny * W + nx]
                            if g and (g - 1) not in dead:
                                mask |= 1 << colOf[g - 1]
                    pending[s] = (t, dc, lastEater.pop(cid, -1), mask)
                else:
                    raise ValueError(f'bad event {k} at tick {t}')
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            # new order: survivors in old order, then this tick's births (minus any that died)
            if dead:
                keep = [i for i, cid in enumerate(ids) if cid not in dead]
                sids = [ids[i] for i in keep]; scols = [cols[i] for i in keep]; sprev = [prev[i] for i in keep]
                for cid in dead:
                    sqOf.pop(cid, None)
            else:
                sids, scols, sprev = ids, cols, prev
            w = win(t)
            base = w * 768
            for cid, c, q, e in zip(sids, scols, sprev, en):
                if cid in touched:
                    touchedN[c * 3 + w] += 1
                    continue
                d = e - q
                if d == 1:
                    R[c * 2304 + base + q * 3 + 1] += 1
                elif d == 0:
                    R[c * 2304 + base + q * 3] += 1
                else:
                    R[c * 2304 + base + q * 3 + 2] += 1
                    kk = (c, w, d); other[kk] = other.get(kk, 0) + 1
            nb = [b for b in births if b not in dead]
            ids = sids + nb
            cols = scols + [colOf[b] for b in nb]
            touchedN_b = len(nb)
            if len(ids) != n:
                val['countMismatch'] += 1
            prev = list(en)
            cur = t + 1
        elif rt == 3:
            ticksRun, reason = struct.unpack_from('<IB', raw, p); p += 5
            plac = list(raw[p:p + 4]); p += 4
            pop = list(U16x4.unpack_from(raw, p)); p += 8
            end = dict(ticksRun=ticksRun, reason=reason, placement=plac, pop=pop)
        elif rt == 4:
            raise ValueError('lite replay (board snapshots) not handled')
        else:
            raise ValueError(f'bad record {rt}')
    for t in sorted(kfs):
        if t == cur:
            check_kf(t)
    T = cur
    for s, pr in pending.items():      # unfilled at the end: fillCol -1, dt = ticks left (censored)
        races.append((pr[0], pr[1], pr[2], pr[3], -1, T - pr[0], 0, -1))
    races.sort()
    rest = {}
    for c in range(4):
        rest[c] = {}
        for w in range(3):
            o = c * 2304 + w * 768
            rest[c][w] = {q: [R[o + q * 3], R[o + q * 3 + 1], R[o + q * 3 + 2]] for q in range(256)
                          if R[o + q * 3] or R[o + q * 3 + 1] or R[o + q * 3 + 2]}
    return dict(id=rid, header=dict(version=version, w=W, h=H, kfEvery=kfe, maxTicks=maxt), ticks=T, end=end,
                validation=val, rest=rest, touched=touchedN, pop=pops, early=early,
                otherDeltas={f'{c},{w},{d}': v for (c, w, d), v in sorted(other.items())}), races


def main():
    global PULL, REP, SUM, OUT
    PULL, args = P.take_pull(sys.argv[1:], 'mine.py')
    REP = os.path.join(ROOT, 'data', PULL, 'replays')
    SUM = os.path.join(ROOT, 'data', PULL, 'summaries')
    OUT = os.path.join(ROOT, 'data', PULL, 'mining')
    below_normal()
    rids = args or sorted(f.split('.')[0] for f in (os.listdir(REP) if os.path.isdir(REP) else [])
                                  if f.endswith('.chr2.gz'))
    if not rids:   # replays are not in the repository
        sys.exit(f'no replays in data/{PULL}/replays: run a pull first (architecture/data-pulls.md)')
    for rid in rids:
        if not os.path.exists(os.path.join(REP, f'{rid}.chr2.gz')):
            sys.exit(f'replay data/{PULL}/replays/{rid}.chr2.gz not found: run a pull first (architecture/data-pulls.md)')
    os.makedirs(os.path.join(OUT, 'races'), exist_ok=True)
    for rid in rids:
        jp = os.path.join(OUT, f'{rid}.json')
        if os.path.exists(jp) and not args:
            continue
        t0 = time.time()
        res, races = mine(rid)
        sp = os.path.join(SUM, f'{rid}.json')
        if os.path.exists(sp):
            names = json.load(open(sp, encoding='utf-8'))['names']
        else:   # data/<pull>/names.json (tab.py) maps id -> colony names in colony order
            names = json.load(open(os.path.join(ROOT, 'data', PULL, 'names.json'), encoding='utf-8'))[str(rid)]
        res['names'] = [n.split(' ', 1)[-1] if not n[:1].isalnum() else n for n in names]   # drop a leading emoji only
        res['seconds'] = round(time.time() - t0, 1)
        with gzip.open(os.path.join(OUT, 'races', f'{rid}.csv.gz'), 'wt', newline='') as f:
            f.write('tDeath,deadCol,killerCol,contMask,fillCol,dt,fillKind,fillE\n')
            for r in races:
                f.write(','.join(map(str, r)) + '\n')
        with open(jp, 'w', encoding='utf-8') as f:
            json.dump(res, f, separators=(',', ':'))
        print(rid, res['ticks'], res['seconds'], 's', res['validation'], len(races), 'deaths', flush=True)


if __name__ == '__main__':
    main()
