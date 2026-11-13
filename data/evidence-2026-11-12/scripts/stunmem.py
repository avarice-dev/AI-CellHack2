"""Scratch (design check b): does a stunned cell keep the memory writes of the call that was cancelled?
Bane v2.2 writes its stored bite inside the call (first bite: bite_tbl scan, then SETLOCK).  If a stunned cell keeps
those writes, a cell stunned at first contact (no stored bite before) bites on the next tick through the stored bite
(4 instructions); if the writes are dropped, it scans again (16).  Event-order cost class (our cells' markers, as
race.py / order.py) of every Bane v2.2 eat on an enemy, by category:
  lock       the rebuilt stored bite (last landed bite) points at the target: a known 4
  first      no rebuilt stored bite, not stunned on the previous tick: a known 16
  stunprev   no rebuilt stored bite, stunned on the previous tick with this same enemy on an edge then: 4 if writes
             persist, 16 if dropped
Usage: python stunmem.py <replay dir> <names.json> <out.csv> [id ...]
"""
import collections
import csv
import gzip
import json
import os
import struct
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))   # append: keep the stdlib ahead of scratch modules
import parents  # noqa: E402
from race import choose, cls, era  # noqa: E402

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))          # UP RIGHT DOWN LEFT
PRIO = (2, 1, 0, 3)                                 # gate split order DOWN, RIGHT, UP, LEFT
FREED = {0: ((-1, -1), (1, -1)), 1: ((1, -1), (2, 0), (1, 1)), 2: ((-1, 1), (1, 1)), 3: ((-1, -1), (-2, 0), (-1, 1))}
RUN = parents.Running()


def rule_store_at(at, enemy, cx, cy, vertical):
    """Part A rest tail, the one precedence (brief v2.3 section 2; the oracle of sim/tests/test_bane4.py).
    at(x, y): 0 = empty, -1 = wall / off the board, > 0 = a cell; enemy(x, y): an enemy cell there.  Returns the
    (x, y) of the square the tail stores a bite on, or None (stored bite left unchanged):
    1. a refill pattern (FREED_BY, as gate 1's thr_tbl = 12): gate 1's first choice (first refill-pattern empty edge
       in gate order DOWN, RIGHT, UP, LEFT);
    2. else (vertical only) the square two below holds an enemy and DOWN is empty: DOWN;
    3. else (vertical only) the square two above holds an enemy and UP is empty: UP;
    4. else None."""
    for k in PRIO:
        x, y = cx + DIRS[k][0], cy + DIRS[k][1]
        if at(x, y) == 0 and any(enemy(cx + a, cy + b) for a, b in FREED[k]):
            return (x, y)
    if vertical:
        if at(cx, cy + 1) == 0 and enemy(cx, cy + 2):
            return (cx, cy + 1)
        if at(cx, cy - 1) == 0 and enemy(cx, cy - 2):
            return (cx, cy - 1)
    return None


def win(t):
    return 'a' if t < 30 else 'b' if t < 60 else 'c' if t < 100 else 'd'


def run(path, bane):
    raw = gzip.decompress(open(path, 'rb').read())
    version, ruleset, W, H, ncol, kfe, seed, maxt = struct.unpack_from('<HHHHBHQI', raw, 4)
    p = 4 + struct.calcsize('<HHHHBHQI') + 16
    U32, U32x2 = struct.Struct('<I'), struct.Struct('<II')
    BIRTH, MOVE = struct.Struct('<IBHHB'), struct.Struct('<IHH')
    colOf, sqOf, enOf = {}, {}, {}
    grid = [0] * (W * H)
    ids, loaded, n_raw = [], False, len(raw)
    out = collections.Counter()
    prev_eats = set()
    lock = {}
    born_at, moved_at = {}, {}
    nbinfo = {}                      # newborn id -> (parent rule, parent square)
    adj_prev = set()                 # (A, X) edge pairs at the previous tick start
    pstate, pgate = {}, {}           # A -> its state on the previous tick / its gate first choice square then
    stun_prev = {}                   # A -> enemies on its edges at the start of the tick it was stunned (prev tick)
    prs1, prs2 = {}, {}              # A -> the part A rule's stored square on the previous tick (as briefed / + 2, 22)
    watch = []                       # [A, t, key] waiting for the 5 / 10 tick death checks
    died_at = {}
    DV = {-W: 0, 1: 1, W: 2, -1: 3}

    def nbrs(s):
        x, y = s % W, s // W
        for dx, dy in DIRS:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                yield (y + dy) * W + x + dx

    def at(snap, x, y):
        return snap[y * W + x] if 0 <= x < W and 0 <= y < H else -1

    def enemy(snap, x, y, c):
        g = at(snap, x, y)
        return g > 0 and colOf[g - 1] != c

    def rule_store(snap, s, c, vertical):
        q = rule_store_at(lambda x, y: at(snap, x, y), lambda x, y: enemy(snap, x, y, c), s % W, s // W, vertical)
        return None if q is None else q[1] * W + q[0]

    def gate_choice(snap, s, c):
        cx, cy = s % W, s // W
        empt = [k for k in PRIO if at(snap, cx + DIRS[k][0], cy + DIRS[k][1]) == 0]
        fr = [k for k in empt if any(enemy(snap, cx + a, cy + b, c) for a, b in FREED[k])]
        k = (fr or empt or [None])[0]
        return (None if k is None else (cy + DIRS[k][1]) * W + cx + DIRS[k][0]), bool(fr)

    while p < n_raw:
        rt = raw[p]; p += 1
        if rt == 2:
            tick, n = U32x2.unpack_from(raw, p); p += 8
            cells = [BIRTH.unpack_from(raw, p + 10 * i) for i in range(n)]; p += 10 * n
            if not loaded:
                for cid, c, x, y, e in cells:
                    ids.append(cid); colOf[cid] = c; sqOf[cid] = y * W + x; grid[y * W + x] = cid + 1; enOf[cid] = e
                loaded = True
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]; p += 4 + 8
            nev = U32.unpack_from(raw, p)[0]; p += 4
            RUN.tick(enOf)
            snap = grid
            sq0 = dict(sqOf)
            grid = snap[:]
            evs, births, dead, acted = [], [], set(), set()
            for _ in range(nev):
                k = raw[p]
                if k in (4, 5):
                    a, b = U32x2.unpack_from(raw, p + 1); p += 10
                    RUN.event(k, a, b)
                    evs.append(('eat' if k == 4 else 'feed', a, b))
                    acted.add(a)
                elif k == 1:
                    cid, c, x, y, e = BIRTH.unpack_from(raw, p + 1); p += 11
                    s = y * W + x
                    cnd = [g - 1 for g in (snap[q] for q in nbrs(s))
                           if g and colOf.get(g - 1) == c and g - 1 not in acted and g - 1 not in dead]
                    par, _tag = RUN.parent(cnd, e)
                    if c == bane:
                        if par is None:
                            nbinfo[cid] = ('?', None)
                        else:
                            ps = sq0[par]
                            _, fr = gate_choice(snap, ps, c)
                            nbinfo[cid] = ('gate' if enOf.get(par, 0) >= (12 if fr else 16) else 'rule4', ps)
                    colOf[cid] = c; sqOf[cid] = s; grid[s] = cid + 1; enOf[cid] = e
                    births.append(cid)
                    born_at[cid] = t
                    evs.append(('split', par, cid))
                    if par is not None:
                        acted.add(par)
                elif k == 2:
                    cid, x, y = MOVE.unpack_from(raw, p + 1); p += 9
                    s0 = sqOf[cid]
                    if grid[s0] == cid + 1:
                        grid[s0] = 0
                    grid[y * W + x] = cid + 1; sqOf[cid] = y * W + x
                    evs.append(('move', cid, None))
                    acted.add(cid)
                    moved_at[cid] = t
                elif k == 3:
                    cid = U32.unpack_from(raw, p + 1)[0]; p += 5
                    dead.add(cid)
                else:
                    raise ValueError(k)
            # event-order markers of our cells' costs (race.py, v2.2 only)
            cost = [None] * len(evs)
            for i, (kind, a, b) in enumerate(evs):
                if a is None or colOf.get(a) != bane:
                    continue
                if kind == 'eat' and colOf.get(b) != bane and (a, b) in prev_eats:
                    cost[i] = 4
                elif kind == 'split':
                    s = sq0.get(a)
                    if s is None or enOf.get(a, 0) < 16 or any(snap[q] and colOf[snap[q] - 1] != bane for q in nbrs(s)):
                        continue
                    cost[i] = 16
                elif kind == 'move':
                    cost[i] = 39
            lo, hi = [0] * len(evs), [999] * len(evs)
            m = 0
            for i in range(len(evs)):
                lo[i] = m
                if cost[i] is not None:
                    m = max(m, cost[i])
            m = 999
            for i in range(len(evs) - 1, -1, -1):
                hi[i] = m
                if cost[i] is not None:
                    m = min(m, cost[i])
            first_eat = {}
            first_bitten, own_act = {}, {}
            for i, (kind, a, b) in enumerate(evs):
                if kind == 'eat':
                    first_eat.setdefault((a, b), i)
                    if colOf.get(a) != colOf.get(b) and b not in first_bitten:
                        first_bitten[b] = i
                if a is not None and a not in own_act:
                    own_act[a] = i
            # stunmem: cost class of our eats by category
            for i, (kind, a, b) in enumerate(evs):
                if kind != 'eat' or colOf.get(a) != bane or colOf.get(b) == bane or own_act.get(a) != i:
                    continue
                if a not in sq0 or b not in sq0:
                    continue
                d = DV.get(sq0[b] - sq0[a])
                L = lock.get(a)
                if L is not None:
                    cat = 'lock' if L == d else 'lock-other'
                elif b in stun_prev.get(a, ()):
                    cat = 'stunprev'
                elif a in stun_prev:
                    cat = 'stunprev-other'
                else:
                    cat = 'first'
                out[(colOf[b], win(t), cat, cls(lo[i], hi[i]))] += 1
            nsp = {}
            for A in ids:
                if colOf.get(A) != bane or A not in sq0:
                    continue
                fb, oa = first_bitten.get(A), own_act.get(A)
                if fb is not None and (oa is None or fb < oa) and lock.get(A) is None:
                    en_ = {snap[q] - 1 for q in nbrs(sq0[A]) if snap[q] and colOf[snap[q] - 1] != bane}
                    if en_:
                        nsp[A] = en_
            stun_prev = nsp
            continue_pairs = False
            # new pairs at this tick start
            adj_now = set()
            w = win(t)
            for A in (ids if continue_pairs else ()):
                if colOf.get(A) != bane or A not in sq0:
                    continue
                s = sq0[A]
                E = {}
                for q in nbrs(s):
                    g = snap[q]
                    if g and colOf[g - 1] != bane:
                        E[DV[q - s]] = g - 1
                for d, X in E.items():
                    adj_now.add((A, X))
                    if (A, X) in adj_prev:
                        continue
                    if born_at.get(X) == t - 1:
                        ent = 'enemy-split'
                    elif moved_at.get(X) == t - 1:
                        ent = 'enemy-move'
                    elif born_at.get(A) == t - 1:
                        ent = 'our-split'
                    elif moved_at.get(A) == t - 1:
                        ent = 'our-move'
                    else:
                        ent = 'other'
                    prev = gatech = nbrule = nblock = nbplace = rs1 = rs2 = '-'
                    if ent.startswith('enemy'):
                        prev = pstate.get(A, '?')
                        gatech = str(int(pgate.get(A) == sq0.get(X)))
                        if prev in ('hold', 'rest<5', 'none-other'):
                            rs1 = str(int(prs1.get(A) == sq0.get(X)))
                            rs2 = str(int(prs2.get(A) == sq0.get(X)))
                    if ent == 'our-split':
                        nbrule, ps = nbinfo.get(A, ('?', None))
                        L = lock.get(A)
                        nblock = 'none' if L is None else 'valid' if L in E else 'stale'
                        if ps is not None:
                            pd = DV.get(s - ps)
                            nbplace = 'ahead' if pd == d else 'side'
                    other = int(len(E) > 1)
                    L = lock.get(A)
                    plan = 'lock' if L is not None and L in E else 'first'
                    iw, ie = first_eat.get((A, X)), first_eat.get((X, A))
                    if iw is not None and (ie is None or iw < ie):
                        res, ec, ed = 'we', '-', '-'
                    elif ie is not None:
                        res, ec = 'enemy', cls(lo[ie], hi[ie])
                        ed = 'UD' if (d + 2) % 4 in (0, 2) else 'LR'
                    else:
                        res, ec, ed = 'neither', '-', '-'
                    flip = '-'
                    if res == 'enemy':
                        flip = '0' if plan == 'lock' else '1' if ec == '5-15' else '0.5' if ec == '=4' else '0'
                    key = (colOf[X], w, ent, prev, other, gatech, nbrule, nblock, nbplace, plan, res, ec, ed, flip, rs1, rs2)
                    pass
            adj_prev = adj_now
            # state of our cells on this tick (for new pairs next tick)
            pstate, pgate = {}, {}
            prs1, prs2 = {}, {}
            for A in ids:
                if colOf.get(A) != bane or A not in sq0:
                    continue
                s = sq0[A]
                fb, oa = first_bitten.get(A), own_act.get(A)
                e = enOf.get(A, 0)
                cx, cy = s % W, s // W
                opn = any(not snap[q] for q in nbrs(s))
                diag = any(enemy(snap, cx + a, cy + b, bane) for a in (-1, 1) for b in (-1, 1))
                if fb is not None and (oa is None or fb < oa):
                    st = 'stunned'
                elif oa is not None:
                    st = 'acted'
                elif not opn:
                    st = 'boxed'
                elif e < 5:
                    st = 'rest<5'
                elif e < 12 and diag:
                    st = 'hold'
                else:
                    st = 'none-other'
                pstate[A] = st
                pgate[A] = gate_choice(snap, s, bane)[0]
                if st in ('hold', 'rest<5', 'none-other'):
                    prs1[A] = rule_store(snap, s, bane, False)
                    prs2[A] = rule_store(snap, s, bane, True)
            # stored bites (race.py): last bite direction, copied to a child
            eats = set()
            for kind, a, b in evs:
                if kind == 'eat' and colOf.get(a) != colOf.get(b):
                    eats.add((a, b))
                    if colOf.get(a) == bane:
                        lock[a] = DV.get(sq0.get(b, -1) - sq0.get(a, -2))
                elif kind == 'split' and a is not None and colOf.get(a) == bane:
                    lock[b] = lock.get(a)
            prev_eats = eats
            for cid in dead:
                died_at[cid] = t
            keep = []
            for it in watch:
                A, t0, key = it
                td = died_at.get(A)
                if td is not None or t - t0 >= 10:
                    d5 = int(td is not None and td - t0 <= 5)
                    d10 = int(td is not None and td - t0 <= 10)
                    out[key + (d5, d10)] += 1
                else:
                    keep.append(it)
            watch = keep
            n = U32.unpack_from(raw, p)[0]; p += 4
            en = raw[p:p + n]; p += n
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
            raise ValueError((rt, p))
    return out


COLS = ['replay', 'rival', 'window', 'cat', 'ecost', 'n']

if __name__ == '__main__':
    rdir, names_path, outp = sys.argv[1:4]
    want = set(sys.argv[4:])
    names = json.load(open(names_path, encoding='utf-8'))
    rows = []
    for f in sorted(os.listdir(rdir)):
        rid = f.split('.')[0]
        if want and rid not in want:
            continue
        nm = [n[:-2] if n.endswith((' W', ' L')) else n for n in names.get(rid, [])]
        bc = [c for c, n in enumerate(nm) if n == 'Bane v2.2']
        if len(bc) != 1 or era(int(rid)) != 'v2.2':
            continue
        out = run(os.path.join(rdir, f), bc[0])
        for key, n in out.items():
            c = key[0]
            rows.append(dict(zip(COLS, [rid, nm[c] if c < len(nm) else 'colony %d' % c] + list(key[1:]) + [n])))
        print(rid, 'done', flush=True)
    with open(outp, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=COLS)
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', outp, len(rows))
