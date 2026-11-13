"""Scratch (review R1): first-contact anatomy for Bane v2.2, from real replays (no models).
A new pair = a Bane cell A and an enemy cell X that are edge neighbours at the start of tick t and were not at the
start of t - 1 (both alive then, or one of them born / moved on t - 1).
Fields per new pair (CSV columns):
  entered   enemy-split (X born on t - 1) / enemy-move (X moved on t - 1) / our-split / our-move / other
  prev      enemy entered: A's state on t - 1: stunned / acted / hold (no event, open, 5-11, enemy on a diagonal) /
            rest<5 / boxed / none-other ('-' otherwise)
  other     an enemy other than X on an edge of A at the start of t (0/1)
  gatech    enemy entered: X's square = A's gate first choice at the start of t - 1 (refill-pattern empty edge first,
            then any empty edge, order DOWN, RIGHT, UP, LEFT; FREED_BY of cells/gen_scourge.py) (0/1, '-' otherwise)
  nbrule    our newborn entered: the parent's rule (gate: parent energy >= 12 with a refill pattern or >= 16; rule4:
            below), '?' if the parent is unknown ('-' otherwise)
  nblock    our newborn entered: inherited stored bite points at an enemy at the start of t (valid) / points elsewhere
            (stale) / none
  nbplace   our newborn entered: X straight ahead of the child (opposite its parent: 'ahead') or beside ('side')
  plan      A's plan on t: lock (stored bite points at an enemy: 4) / first (bite_tbl scan: 16)
  result    on t, between A and X: we (A bit X before X bit A) / enemy (X bit A first) / neither
  ecost     result enemy: X's bite cost class from our cells' event-order markers (<4, =4, 5-15, =16, >16, other)
  edir      result enemy: X's bite direction from X's side (UD / LR)
  rs1, rs2  enemy entered: the v2.3 part A rule (rest tail only: prev = hold / rest<5 / none-other) would have stored
            the entered square at the start of t - 1: rs1 = refill pattern as in Bane (FREED_BY: beyond only LEFT /
            RIGHT, view 10 / 14), rs2 = the brief's precedence: refill pattern first, else DOWN if view 22 is an
            enemy, else UP if view 2 is an enemy (rule_store).  0/1, '-' otherwise
  flip      first-order flip if A's bite cost 4 (s15): result enemy and plan first: 5-15 -> 1, =4 -> 0.5, else 0
  d5, d10   A dead within 5 / 10 ticks of t (0/1)
Split parents: energy-matched (parents.py).  Windows: a t < 30, b < 60, c < 100, d later.
Usage: python first_contact.py <replay dir> <names.json> <out.csv> [id ...]
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
        """Part A rest tail, the one precedence (brief section 2; also the oracle of the table-driven test):
        1. a refill pattern (FREED_BY, as gate 1's thr_tbl = 12): gate 1's first choice (first refill-pattern empty
           edge in gate order DOWN, RIGHT, UP, LEFT);
        2. else (vertical only) view idx 22 holds an enemy and DOWN is empty: DOWN;
        3. else (vertical only) view idx 2 holds an enemy and UP is empty: UP;
        4. else None (the stored bite is left unchanged)."""
        cx, cy = s % W, s // W
        for k in PRIO:
            if at(snap, cx + DIRS[k][0], cy + DIRS[k][1]) == 0 and \
                    any(enemy(snap, cx + a, cy + b, c) for a, b in FREED[k]):
                return (cy + DIRS[k][1]) * W + cx + DIRS[k][0]
        if vertical:
            if at(snap, cx, cy + 1) == 0 and enemy(snap, cx, cy + 2, c):
                return (cy + 1) * W + cx
            if at(snap, cx, cy - 1) == 0 and enemy(snap, cx, cy - 2, c):
                return (cy - 1) * W + cx
        return None

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
            # new pairs at this tick start
            adj_now = set()
            w = win(t)
            for A in ids:
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
                    watch.append([A, t, key])
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
    for A, t0, key in watch:                          # game over: survived to the end
        out[key + (0, 0)] += 1
    return out


COLS = ['replay', 'rival', 'window', 'entered', 'prev', 'other', 'gatech', 'nbrule', 'nblock', 'nbplace', 'plan',
        'result', 'ecost', 'edir', 'flip', 'rs1', 'rs2', 'd5', 'd10', 'n']

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
