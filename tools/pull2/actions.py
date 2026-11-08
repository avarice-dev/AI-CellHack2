"""What a cell does when it has an enemy neighbour: per colony, per enemy-neighbour pattern, the share of cell-ticks
that ate in each direction, fed, split (a same-colony birth next to it that it could be the parent of), moved, or had
no event (rested / stunned / blocked). Measured from the replay events, start-of-tick board.

Usage: python -I tools/pull2/actions.py <replay id> [colony ...]   (reads data/<CH_PULL or pull2>/replays/<id>.chr2.gz)
Prints one table per colony: key = enemy directions at start of tick (U R D L), then counts and shares.
Splits are attributed to every same-colony neighbour of the child that is not otherwise busy (ambiguous when
several), so 'split' is an upper bound. Event order is turn order; 'bitten first' = eaten before its own action.
"""
import gzip, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PULL = os.environ.get('CH_PULL', 'pull2')
REP = os.path.join(ROOT, 'data', PULL, 'replays')
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))   # U R D L
DN = 'URDL'


def run(rid, want, tmin=0, tmax=10 ** 9, emin=0, emax=255):
    raw = gzip.decompress(open(os.path.join(REP, f'{rid}.chr2.gz'), 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids = []
    loaded = False
    stats = {}          # (colony, enemy mask) -> counter dict
    n_raw = len(raw)
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
            own = {}            # cid -> first own action ('e'+dir, 'f'+dir, 'm')
            bitten_first = set()
            births = []
            dead = set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    if a not in own:
                        sa, sb = sqOf[a], sqOf[b]
                        dx, dy = sb % W - sa % W, sb // W - sa // W
                        d = DIRS.index((dx, dy)) if (dx, dy) in DIRS else 4
                        own[a] = ('e' if k == 4 else 'f') + (DN[d] if d < 4 else '?')
                    if k == 4 and b not in own:
                        bitten_first.add(b)
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                    births.append(cid)
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    own.setdefault(cid, 'm')
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            # split parents: same-colony start-of-tick neighbours of each child with no other action
            splitters = set()
            for b in births:
                s = sqOf[b]; x, y = s % W, s // W
                for dx, dy in DIRS:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H:
                        g = snap[ny * W + nx]
                        if g and colOf[g - 1] == colOf[b] and (g - 1) not in own:
                            splitters.add(g - 1)
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            if tmin <= t < tmax:
                for cid in ids:
                    c = colOf[cid]
                    if want and c not in want:
                        continue
                    e0 = enOf.get(cid, 0)
                    if not emin <= e0 <= emax:
                        continue
                    s = sqOf.get(cid) if cid not in own or own[cid] != 'm' else None
                    if s is None:
                        continue
                    x, y = s % W, s // W
                    mask = ''
                    for i, (dx, dy) in enumerate(DIRS):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H:
                            g = snap[ny * W + nx]
                            if g and colOf[g - 1] != c:
                                mask += DN[i]
                    if not mask:
                        continue
                    a = own.get(cid)
                    if a is None:
                        a = 'split?' if cid in splitters else ('bitten-first' if cid in bitten_first else 'none')
                    st = stats.setdefault((c, mask), {})
                    st[a] = st.get(a, 0) + 1
            # tidy: remove dead, new order = survivors then births (energies follow that order)
            for cid in dead:
                s = sqOf.pop(cid, None)
                if s is not None and grid[s] == cid + 1:
                    grid[s] = 0
            ids = [i for i in ids if i not in dead] + [b for b in births if b not in dead]
            for cid, e in zip(ids, en):
                enOf[cid] = e
        elif rt == 3:
            p += 5 + 4 + 8
        else:
            raise ValueError((rt, p, n_raw))
    return stats


def main():
    rid = int(sys.argv[1])
    want = {int(a) for a in sys.argv[2:] if not a.startswith('-')}
    opt = dict(a[2:].split('=') for a in sys.argv[2:] if a.startswith('--'))
    st = run(rid, want, int(opt.get('tmin', 0)), int(opt.get('tmax', 10 ** 9)), int(opt.get('emin', 0)),
             int(opt.get('emax', 255)))
    for (c, mask), d in sorted(st.items(), key=lambda kv: (kv[0][0], -sum(kv[1].values()))):
        tot = sum(d.values())
        if tot < 200:
            continue
        top = sorted(d.items(), key=lambda kv: -kv[1])[:7]
        print(f'col {c} enemy {mask:<4} n {tot:>7}  ' + '  '.join(f'{a} {100 * v / tot:.0f}%' for a, v in top))


if __name__ == '__main__':
    main()
