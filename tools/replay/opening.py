"""Opening moves and splits of one colony: per tick, every MOVE (mover's energy, from, to, empty orthogonal neighbours
before and after, distance from the colony's centre before and after) and the births; plus a summary: moves by
mover energy, share that gained empty neighbours, share outward; cells that had an empty neighbour and e >= 5 and
did not split (holds).  Start-of-tick board.

Usage: python -I tools/replay/opening.py --pull <pull> <replay id> <colony index> [--tmin=0] [--tmax=40] [--quiet]
"""
import collections, gzip, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulls as P  # noqa: E402
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def run(path, col, tmin, tmax, quiet):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded = [], False
    by_e = collections.Counter(); gained = outward = nmoves = 0
    holds = collections.Counter(); splits_e = collections.Counter()
    n_raw = len(raw)

    def empties(s, g):
        x, y = s % W, s // W
        return sum(1 for dx, dy in DIRS if 0 <= x + dx < W and 0 <= y + dy < H and not g[(y + dy) * W + x + dx])

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
            mine = [cid for cid in ids if colOf[cid] == col]
            if mine:
                cx = sum(sqOf[c] % W for c in mine) / len(mine); cy = sum(sqOf[c] // W for c in mine) / len(mine)
            acted = set(); births = []; dead = set(); moves = []
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    acted.add(a)
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1
                    births.append(cid)
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]; s1 = y * W + x
                    if colOf[cid] == col and tmin <= t < tmax:
                        e0, e1 = empties(s0, snap), empties(s1, snap) - 0
                        d0 = abs(s0 % W - cx) + abs(s0 // W - cy); d1 = abs(x - cx) + abs(y - cy)
                        moves.append((enOf.get(cid, 0), s0 % W, s0 // W, x, y, e0, e1, round(d1 - d0, 1)))
                        by_e[enOf.get(cid, 0)] += 1; nmoves += 1; gained += e1 > e0; outward += d1 > d0
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[s1] = cid + 1; sqOf[cid] = s1
                    acted.add(cid)
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            if tmin <= t < tmax:
                parents = set()
                for b in births:
                    if colOf[b] != col:
                        continue
                    x, y = sqOf[b] % W, sqOf[b] // W
                    for dx, dy in DIRS:
                        if 0 <= x + dx < W and 0 <= y + dy < H:
                            g = snap[(y + dy) * W + x + dx]
                            if g and colOf[g - 1] == col and (g - 1) not in acted:
                                parents.add(g - 1)
                for cid in mine:
                    if cid in acted or cid in parents:
                        continue
                    if enOf.get(cid, 0) >= 5 and empties(sqOf[cid], snap):
                        holds[enOf[cid]] += 1
                for cid in parents:
                    splits_e[enOf.get(cid, 0)] += 1
                if not quiet:
                    nb = sum(1 for b in births if colOf[b] == col)
                    print('t%-3d pop %4d births %3d moves %2d  %s' % (
                        t, len(mine), nb, len(moves), ' '.join('e%d:(%d,%d)->(%d,%d) emp%d->%d d%+.1f' % m for m in moves[:6])))
            for cid in dead:
                s = sqOf.pop(cid, None)
                if s is not None and grid[s] == cid + 1:
                    grid[s] = 0
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
            ids = [i for i in ids if i not in dead] + [b for b in births if b not in dead]
            for cid, e in zip(ids, en):
                enOf[cid] = e
            if t >= tmax:
                break
        elif rt == 3:
            p += 5 + 4 + 8
        else:
            raise ValueError((rt, p))
    print('moves %d: by energy %s; gained empties %d (%.0f%%); outward %d (%.0f%%)' % (
        nmoves, dict(sorted(by_e.items())), gained, 100 * gained / max(nmoves, 1), outward, 100 * outward / max(nmoves, 1)))
    print('split parents by energy (start of tick): %s' % dict(sorted(splits_e.items())))
    print('holds (e >= 5, empty neighbour, no action) by energy: %s' % dict(sorted(holds.items())))


def main():
    pull, argv = P.take_pull(sys.argv[1:], 'opening.py')
    pos = [a for a in argv if not a.startswith('--')]
    if len(pos) < 2:
        sys.exit('usage: python -I tools/replay/opening.py --pull <pull> <replay id> <colony index> [--tmin=0] [--tmax=40] [--quiet]')
    opt = dict(a[2:].split('=') if '=' in a else (a[2:], '1') for a in argv if a.startswith('--'))
    path = os.path.join(ROOT, 'data', pull, 'replays', f'{pos[0]}.chr2.gz')
    run(path, int(pos[1]), int(opt.get('tmin', 0)), int(opt.get('tmax', 40)), 'quiet' in opt)


if __name__ == '__main__':
    main()
