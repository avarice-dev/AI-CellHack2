"""Who could have taken a freed square, and what they did instead.  For every death at tick t (square s free at
t+1), every cell orthogonally adjacent to s at the start of t+1 is a candidate.  Per replay and colony, split into
own squares (the dead cell's colony) and enemy squares: how many candidate cells, their energy (share below 12 =
our refill floor), how many had another enemy orthogonal neighbour (our kernel bites instead of splitting), what
they did at t+1 (eat / feed / split into s / other split / move / bitten first / none), and who filled s at t+1.

Usage: python -I tools/replay/claims.py --pull <pull> <replay id> [--tmin=T] [--tmax=T]
"""
import collections, gzip, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulls as P  # noqa: E402
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def run(path, names, tmin, tmax):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded = [], False
    freed = {}                      # square -> (tDeath, deadCol)
    sq = collections.Counter()      # (colony, role) -> squares with >= 1 candidate of that colony
    filled = collections.Counter()  # (colony, role, filler class) -> n
    cand = collections.Counter()    # (colony, role, key) -> n candidate cells
    fill_e = collections.defaultdict(list)
    n_raw = len(raw)

    def nbrs(s):
        x, y = s % W, s // W
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H:
                yield ny * W + nx

    while p < n_raw:
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8
            cells = []
            for _ in range(n):
                cells.append(BIRTH.unpack_from(raw, p)); p += 10
            if not loaded:
                for cid, c, x, y, e in cells:
                    ids.append(cid); colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                loaded = True
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 4 + 8
            nev = U32.unpack_from(raw, p)[0]; p += 4
            snap = grid[:]
            # candidates of the squares freed last tick
            todo = {}
            for s, (td, dc) in list(freed.items()):
                if td == t - 1:
                    cs = []
                    for q in nbrs(s):
                        g = snap[q]
                        if g:
                            cs.append(g - 1)
                    todo[s] = (dc, cs)
                    del freed[s]
            own, bitten_first, births, dead = {}, set(), [], set()
            born_at, moved_to = {}, {}
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    own.setdefault(a, 'eat' if k == 4 else 'feed')
                    if k == 4 and b not in own:
                        bitten_first.add(b)
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                    births.append(cid); born_at[y * W + x] = (c, e)
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    own.setdefault(cid, 'move'); moved_to[y * W + x] = colOf[cid]
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            splitters = set()
            for b in births:
                for q in nbrs(sqOf[b]):
                    g = snap[q]
                    if g and colOf[g - 1] == colOf[b] and (g - 1) not in own:
                        splitters.add(g - 1)
            if tmin <= t < tmax:
                for s, (dc, cs) in todo.items():
                    fc = born_at[s][0] if s in born_at else moved_to.get(s, -1)
                    if s in born_at:
                        fill_e[fc].append(born_at[s][1])
                    seen = set()
                    for cid in cs:
                        c = colOf[cid]
                        role = 'own' if c == dc else 'enemy'
                        if c not in seen:
                            seen.add(c)
                            sq[c, role] += 1
                            filled[c, role, 'self' if fc == c else 'own' if fc == dc else 'none' if fc < 0 else 'other'] += 1
                        k = 0
                        for q in nbrs(sqOf[cid]):
                            g = snap[q]
                            if g and colOf[g - 1] != c:
                                k += 1
                        a = own.get(cid)
                        if a is None:
                            a = ('split_s' if (s in born_at and born_at[s][0] == c) else 'split') if cid in splitters \
                                else ('bitten' if cid in bitten_first else 'none')
                        e = enOf.get(cid, 0)
                        cand[c, role, 'n'] += 1
                        cand[c, role, 'e<12'] += e < 12
                        cand[c, role, 'e<24'] += e < 24
                        cand[c, role, 'enemy_nbr'] += k >= 1
                        cand[c, role, 'enemy_nbr2'] += k >= 2
                        cand[c, role, 'act_' + a] += 1
                        cand[c, role, 'esum'] += e
                        cand[c, role, ('enb_' if k else 'free_') + a] += 1
                        cand[c, role, 'enb_n' if k else 'free_n'] += 1
            for cid in dead:
                s = sqOf.get(cid)
                if s is not None:
                    freed[s] = (t, colOf[cid])
                    if grid[s] == cid + 1:
                        grid[s] = 0
                sqOf.pop(cid, None)
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            ids = [i for i in ids if i not in dead] + [b for b in births if b not in dead]
            for cid, e in zip(ids, en):
                enOf[cid] = e
        elif rt == 3:
            p += 5 + 4 + 8
        else:
            raise ValueError((rt, p))
    acts = ('eat', 'feed', 'split_s', 'split', 'move', 'bitten', 'none')
    print('colony          role    sq  self%  own%  oth%  none% |  cells  e_mean  e<12%  e<24%  enb%  enb2% | ' +
          ' '.join('%6s' % a for a in acts) + ' | fill_e')
    for (c, role) in sorted(sq, key=lambda k: (k[0], k[1] != 'enemy')):
        n = sq[c, role]
        m = cand[c, role, 'n'] or 1
        f = lambda k: 100 * filled[c, role, k] / n
        g = lambda k: 100 * cand[c, role, k] / m
        fe = fill_e[c]
        print('%-15s %-5s %5d %5.0f%% %4.0f%% %4.0f%% %5.0f%% | %6d %7.1f %5.0f%% %5.0f%% %4.0f%% %5.0f%% | ' %
              (names[c], role, n, f('self'), f('own'), f('other'), f('none'), m, cand[c, role, 'esum'] / m,
               g('e<12'), g('e<24'), g('enemy_nbr'), g('enemy_nbr2')) +
              ' '.join('%5.0f%%' % g('act_' + a) for a in acts) +
              (' | %.1f' % (sum(fe) / len(fe)) if fe else ''))
        for pre in ('enb', 'free'):
            m2 = cand[c, role, pre + '_n'] or 1
            print('    %-4s n %6d: ' % (pre, m2) +
                  '  '.join('%s %.0f%%' % (a, 100 * cand[c, role, pre + '_' + a] / m2) for a in acts))


def main():
    pull, argv = P.take_pull(sys.argv[1:], 'claims.py')
    if not argv or not argv[0].isdigit():
        sys.exit('usage: python -I tools/replay/claims.py --pull <pull> <replay id> [--tmin=T] [--tmax=T]')
    rid = argv[0]
    opt = dict(a[2:].split('=') for a in argv[1:] if a.startswith('--'))
    names = P.names_of(pull, rid) if hasattr(P, 'names_of') else \
        __import__('json').load(open(os.path.join(ROOT, 'data', pull, 'names.json'), encoding='utf-8'))[rid]
    path = os.path.join(ROOT, 'data', pull, 'replays', f'{rid}.chr2.gz')
    print(f'replay {rid} ({", ".join(names)}), t {opt.get("tmin", 0)}-{opt.get("tmax", "end")}')
    run(path, names, int(opt.get('tmin', 0)), int(opt.get('tmax', 10 ** 9)))


if __name__ == '__main__':
    main()
