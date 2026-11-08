"""CellHack2 stage-1 rules engine (rules-only model, Python policies).

Spec: docs/Rules _ CellHack2.pdf (ruleset v9), docs/Reference _ CellHack2.pdf, docs/cellhack.inc (ABI 4).
Every place where the docs are silent is marked "ASSUMPTION" and listed in README.md.

A policy is a plain function  policy(view, mem) -> (action_byte, insn_count)
  view : View, a read-only snapshot built from the board at the start of the tick
  mem  : bytearray(64), the cell's persistent memory (mutate it in place)
It must keep no state of its own between calls (the real asm cell cannot).

Board representation (hot loop): one flat list `grid` over a board padded by 2 squares of wall on every
side, index p = (y + 2) * PW + (x + 2) with PW = W + 4.  grid[p] is a cell id (>= 0), GRID_EMPTY or
GRID_WALL.  Per-cell data lives in parallel lists indexed by cell id.  A cell that dies mid-tick keeps
its id in `grid` (it holds the square) with c_alive False until Tidy removes it.
"""

import random
import struct

# ---- constants from cellhack.inc ----------------------------------------------------------------
CELL_EMPTY, CELL_FRIEND, CELL_ENEMY, CELL_WALL = 0, 1, 2, 3
DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT = 0, 1, 2, 3
ACT_NOP, ACT_REST, ACT_MOVE, ACT_SPLIT, ACT_EAT, ACT_FEED = 0x00, 0x01, 0x10, 0x20, 0x30, 0x40
ACT_DIR_MASK = 0x03
VIEW_CENTER, VIEW_UP, VIEW_RIGHT, VIEW_DOWN, VIEW_LEFT = 12, 7, 13, 17, 11
VIEW_DIR = (VIEW_UP, VIEW_RIGHT, VIEW_DOWN, VIEW_LEFT)  # view index of the neighbour in direction d
MEM_SIZE = 64
INSN_BUDGET = 1000
ENERGY_START = 10
ENERGY_MAX = 50
REST_GAIN = 1
SPLIT_MIN = 5
EAT_TAKE = 2
FEED_AMOUNT = 2
MAX_COLONIES = 4

VALID_ACTIONS = frozenset([ACT_NOP, ACT_REST] +
                          [base + d for base in (ACT_MOVE, ACT_SPLIT, ACT_EAT, ACT_FEED) for d in range(4)])
_VALID = [False] * 256
for _a in VALID_ACTIONS:
    _VALID[_a] = True

FAULT_CRASH = 'crash'          # policy raised, returned None or a malformed value
FAULT_BAD_ACTION = 'bad_action'
FAULT_BUDGET = 'budget'        # insn_count > INSN_BUDGET
FAULT_LOG_MAX = 20             # first N faults per colony are logged in detail (like the match page)

GRID_EMPTY = -1
GRID_WALL = -2
_CODE_EMPTY = 4                # snapshot colony codes: 0..3 colony, 4 empty, 5 wall
_CODE_WALL = 5

# ASSUMPTION: slot -> corner order.  The docs only say "one per corner".
CORNER_ORDER = ('top-left', 'top-right', 'bottom-left', 'bottom-right')

# ---- start placement -----------------------------------------------------------------------------
# Verified 2026-11-08 (replays): ladder starts are random squares, not corners, one cell at energy 10 per
# colony.  Pull 2 (36 replays, data/ladder-data-2-2026-11-08.md s5): the closest pair of starts in a match
# is Manhattan 8 to 42 apart (median 18), so the default minimum is Manhattan 8 (the observed minimum;
# 98753 has a Chebyshev-11 pair).  Nearest-edge distance: 19% of starts within 4 of an edge vs 29% for a
# uniform square, a mild bias not modelled.  Change it here or pass start_sampler.
START_MODES = ('corner', 'random', 'fixed')
DEFAULT_START_MIN_DIST = 8
DEFAULT_START_METRIC = 'manhattan'


def start_distance(a, b, metric):
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    if metric == 'chebyshev':
        return dx if dx > dy else dy
    if metric == 'manhattan':
        return dx + dy
    raise ValueError("metric must be 'manhattan' or 'chebyshev'")


def starts_ok(points, min_dist, metric):
    """True if every pair of points is at least min_dist apart."""
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if start_distance(points[i], points[j], metric) < min_dist:
                return False
    return True


def sample_starts_uniform(rng, width, height, n, min_dist=DEFAULT_START_MIN_DIST,
                          metric=DEFAULT_START_METRIC, tries=20000):
    """n squares, each uniform over the board, conditioned on pairwise distance >= min_dist.

    Rejection sampling of whole sets, so the result is exactly the conditioned uniform distribution.
    Raises ValueError when no valid set turns up in `tries` draws (board too small for the distance).
    """
    for _ in range(tries):
        pts = [(rng.randrange(width), rng.randrange(height)) for _ in range(n)]
        if starts_ok(pts, min_dist, metric):
            return pts
    raise ValueError('no start set with min %s distance %d found on %dx%d for %d colonies'
                     % (metric, min_dist, width, height, n))


# name -> sampler(rng, width, height, n, min_dist=..., metric=...).  Add empirical samplers here (e.g.
# drawn from collected real start sets) and select them by name (picklable for worker processes).
START_SAMPLERS = {'uniform': sample_starts_uniform}


def _first(item):
    return item[0]


class _TickCtx(object):
    """Per-tick data shared by all views of one tick."""
    __slots__ = ('tick', 'w', 'h', 'sc', 'se', 'offs', 'tts', 'self_type')


class View(object):
    """Snapshot handed to a policy.  Field names follow cellhack.inc (VIEW_TICK -> view.tick ...).

    cells and energies are 25-entry lists, row-major, self at index 12 (VIEW_CENTER); they are built
    lazily on first access (same values either way: they come from the start-of-tick snapshot).
    """
    __slots__ = ('tick', 'energy', 'rand', 'age', 'x', 'y', 'w', 'h', 'pop_self', 'pop_enemy', 'colony',
                 '_p', '_ctx', '_cells', '_energies')

    def __init__(self, ctx, p, energy, rand, age, x, y, pop_self, pop_enemy, colony):
        self.tick = ctx.tick
        self.w = ctx.w
        self.h = ctx.h
        self.energy = energy
        self.rand = rand
        self.age = age
        self.x = x
        self.y = y
        self.pop_self = pop_self
        self.pop_enemy = pop_enemy
        self.colony = colony
        self._p = p
        self._ctx = ctx
        self._cells = None
        self._energies = None

    @property
    def cells(self):
        c = self._cells
        if c is None:
            ctx = self._ctx
            p = self._p
            sc = ctx.sc
            tt = ctx.tts[self.colony]
            c = [tt[sc[p + o]] for o in ctx.offs]
            c[VIEW_CENTER] = ctx.self_type
            self._cells = c
        return c

    @property
    def energies(self):
        e = self._energies
        if e is None:
            ctx = self._ctx
            p = self._p
            se = ctx.se
            e = [se[p + o] for o in ctx.offs]
            self._energies = e
        return e

    def to_bytes(self):
        """The 128-byte view struct exactly as the Reference lays it out (for stage 2 / cross-checks)."""
        b = bytearray(128)
        struct.pack_into('<IBxBBHHHHHHB', b, 0, self.tick & 0xFFFFFFFF, self.energy & 0xFF, self.rand,
                         self.age, self.x, self.y, self.w, self.h, self.pop_self & 0xFFFF,
                         self.pop_enemy & 0xFFFF, self.colony)
        b[32:57] = bytes(self.cells)
        b[64:89] = bytes(min(255, v) for v in self.energies)
        return bytes(b)


class Engine(object):
    """One match.

    policies: list of up to 4 entries (index = colony slot); None leaves the slot empty.
    Parameters marked ASSUMPTION are unverified against the real game.
    """

    def __init__(self, policies, width=64, height=64, seed=0, max_ticks=3000,
                 start_inset=0,               # ASSUMPTION: 0 = true corners
                 split_child_rounding='floor',  # ASSUMPTION: child gets floor(e/2), parent keeps the rest
                 cap_mid_tick=False,          # ASSUMPTION: energy may exceed 50 until Tidy (rules text)
                 self_type=CELL_FRIEND,       # ASSUMPTION: what view.cells[12] holds for yourself
                 place_start=True,
                 order_by_alt=False,          # order by the optional 3rd return value (no taken jumps)
                 start_mode='corner',         # 'corner' (old default), 'random' (ladder), 'fixed'
                 start_min_dist=DEFAULT_START_MIN_DIST, start_metric=DEFAULT_START_METRIC,
                 start_positions=None,        # 'fixed': one (x, y) per slot
                 start_sampler=None,          # 'random': name in START_SAMPLERS or callable(rng, w, h, n)
                 stun_keeps_memory=True,      # ASSUMPTION: a stunned cell's memory writes persist
                 record_events=False,         # keep the bite-order pair matrix (bite_first)
                 feed_bonus=0,                # OPTION: extra energy a fed cell gains (pull 2: often +3)
                 idle_gain_prob=0.0,          # OPTION: P(+1) for a cell with no event and no REST
                 record_deltas=False,         # per-cell-tick energy change histograms (deltas)
                 record_races=False):         # one row per death: who refilled the square (race_rows)
        if len(policies) > MAX_COLONIES:
            raise ValueError('at most 4 colonies')
        if split_child_rounding not in ('floor', 'ceil'):
            raise ValueError("split_child_rounding must be 'floor' or 'ceil'")
        self.policies = list(policies) + [None] * (MAX_COLONIES - len(policies))
        self.present = [p is not None for p in self.policies]
        self.W = width
        self.H = height
        self.max_ticks = max_ticks
        self.split_ceil = split_child_rounding == 'ceil'
        self.cap_mid_tick = cap_mid_tick
        self.self_type = self_type
        self.order_by_alt = order_by_alt
        self.rng = random.Random(seed)
        self.seed = seed
        if start_mode not in START_MODES:
            raise ValueError('start_mode must be one of %s' % (START_MODES,))
        self.start_mode = start_mode
        self.stun_keeps_memory = stun_keeps_memory
        self._saved = None             # this tick's pre-call memory copies (stun_keeps_memory False)
        self.record_events = record_events
        if feed_bonus < 0 or not 0.0 <= idle_gain_prob <= 1.0:
            raise ValueError('feed_bonus must be >= 0 and idle_gain_prob in [0, 1]')
        self.feed_bonus = feed_bonus
        self.idle_gain_prob = idle_gain_prob
        # own RNG for the idle gain, so turning it on leaves the match RNG stream unchanged
        self._idle_rng = random.Random('%r/idle' % (seed,)) if idle_gain_prob > 0 else None
        # record_deltas: {'idle': {delta: n}, 'fed': {delta: n}}; delta = energy after Tidy minus energy
        # at the start of the tick.  'idle' = no event on the cell (REST and NOP and faults count as no
        # event, as the replays log no rest event), 'fed' = fed exactly once and no other event.
        # Cells that died or were born in the tick are left out.
        self.deltas = {'idle': {}, 'fed': {}} if record_deltas else None
        self._ev = self._fed = self._rested = None

        PW = width + 4
        PH = height + 4
        self.PW = PW
        self.grid = [GRID_WALL] * (PW * PH)
        self._tmpl_code = [_CODE_WALL] * (PW * PH)
        for y in range(height):
            for x in range(width):
                p = (y + 2) * PW + (x + 2)
                self.grid[p] = GRID_EMPTY
                self._tmpl_code[p] = _CODE_EMPTY
        self._tmpl_zero = [0] * (PW * PH)
        self.dirs = (-PW, 1, PW, -1)          # DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT
        self.offs = tuple(dy * PW + dx for dy in range(-2, 3) for dx in range(-2, 3))
        tts = []
        for c in range(MAX_COLONIES):
            tt = [CELL_ENEMY] * 6
            tt[c] = CELL_FRIEND
            tt[_CODE_EMPTY] = CELL_EMPTY
            tt[_CODE_WALL] = CELL_WALL
            tts.append(tt)
        self._tts = tts

        # per-cell parallel lists, indexed by cell id
        self.c_pos = []
        self.c_col = []
        self.c_en = []
        self.c_born = []     # tick of the first decide this cell takes part in
        self.c_mem = []
        self.c_alive = []
        self.c_done = []     # tick in which the cell last had its turn or was stunned
        self.live = []       # ids of living cells, in birth order (decide / VIEW_RAND order)

        self.tick = 0        # next tick to run (0-based)
        self.finished = False
        self.pop = [0] * MAX_COLONIES
        self.energy = [0] * MAX_COLONIES
        self.death_tick = [None] * MAX_COLONIES    # tick during which the colony's last cell died
        self.insn_total = [0] * MAX_COLONIES
        self.calls = [0] * MAX_COLONIES
        self.insn_max = [0] * MAX_COLONIES
        self.faults = [dict() for _ in range(MAX_COLONIES)]
        self.fault_log = [[] for _ in range(MAX_COLONIES)]
        self.stuns = [0] * MAX_COLONIES            # times a cell of this colony lost its action to a bite
        self.births = [0] * MAX_COLONIES
        self.deaths = [0] * MAX_COLONIES
        # successful actions per colony (always counted; cheap)
        self.moves = [0] * MAX_COLONIES
        self.feeds = [0] * MAX_COLONIES            # feeds that reached a living cell (any colony)
        self.eats_enemy = [0] * MAX_COLONIES       # eats that hit a living cell of another colony
        self.eats_friend = [0] * MAX_COLONIES
        # record_events: bite_first[a][b] = same-tick pairs of successful eats (any target) in which a
        # colony-a eat came before a colony-b eat in turn order (the count taken from the replay events)
        self.bite_first = [[0] * MAX_COLONIES for _ in range(MAX_COLONIES)] if record_events else None
        # record_events: split_energy[c] = {parent energy just before a successful split: count}
        self.split_energy = [dict() for _ in range(MAX_COLONIES)] if record_events else None
        # record_races: rows (tDeath, deadCol, killerCol, contMask, fillCol, dt, fillKind, fillE) as in
        # tools/pull2/mine.py; killer = colony of the last cell that ever ate the dead cell (-1 none),
        # contMask = colonies with a living cell orthogonally adjacent at the moment of death.
        self.races = [] if record_races else None
        self._race_pending = {}         # grid index -> (tDeath, deadCol, killerCol, contMask)
        self._last_eater = {}           # cell id -> colony of its last eater
        self.start_positions = {}

        if place_start:
            slots = [c for c in range(MAX_COLONIES) if self.present[c]]
            if start_mode == 'corner':
                k = start_inset
                corners = ((k, k), (width - 1 - k, k), (k, height - 1 - k), (width - 1 - k, height - 1 - k))
                pts = [corners[c] for c in slots]
            elif start_mode == 'fixed':
                if start_positions is None:
                    raise ValueError("start_mode 'fixed' needs start_positions")
                pts = [tuple(start_positions[c]) for c in slots]
            else:
                smp = start_sampler if start_sampler is not None else 'uniform'
                if callable(smp):
                    pts = smp(self.rng, width, height, len(slots))
                else:
                    pts = START_SAMPLERS[smp](self.rng, width, height, len(slots),
                                              min_dist=start_min_dist, metric=start_metric)
            for c, (x, y) in zip(slots, pts):
                self.start_positions[c] = (x, y)
                self.add_cell(x, y, c, ENERGY_START)

    # ---- setup helpers ---------------------------------------------------------------------------
    def add_cell(self, x, y, colony, energy=ENERGY_START, mem=None, age=0):
        """Place a cell (setup / tests).  age = its VIEW_AGE on the next tick to run."""
        if not (0 <= x < self.W and 0 <= y < self.H):
            raise ValueError('outside the board')
        p = (y + 2) * self.PW + (x + 2)
        if self.grid[p] != GRID_EMPTY:
            raise ValueError('square occupied')
        if not 1 <= energy:
            raise ValueError('energy must be >= 1')
        m = bytearray(MEM_SIZE)
        if mem is not None:
            m[:len(mem)] = mem
        i = len(self.c_pos)
        self.c_pos.append(p)
        self.c_col.append(colony)
        self.c_en.append(energy)
        self.c_born.append(self.tick - age)
        self.c_mem.append(m)
        self.c_alive.append(True)
        self.c_done.append(-1)
        self.live.append(i)
        self.grid[p] = i
        self.pop[colony] += 1
        self.energy[colony] += energy
        self.present[colony] = True
        return i

    def pos_of(self, i):
        p = self.c_pos[i]
        return p % self.PW - 2, p // self.PW - 2

    def cell_at(self, x, y):
        """Cell id at (x, y) or None (includes a cell that died this tick and still holds the square)."""
        g = self.grid[(y + 2) * self.PW + (x + 2)]
        return g if g >= 0 else None

    def cells(self):
        """List of (id, x, y, colony, energy) for living cells."""
        out = []
        for i in self.live:
            if self.c_alive[i]:
                x, y = self.pos_of(i)
                out.append((i, x, y, self.c_col[i], self.c_en[i]))
        return out

    # ---- one tick ----------------------------------------------------------------------------------
    def step(self):
        """Run one tick.  Returns False once the match has ended (then does nothing)."""
        if self.finished:
            return False
        t = self.tick
        grid = self.grid
        pos = self.c_pos
        col = self.c_col
        en = self.c_en
        born = self.c_born
        mems = self.c_mem
        alive = self.c_alive
        done = self.c_done
        live = self.live
        PW = self.PW
        pols = self.policies
        valid = _VALID
        insn_total = self.insn_total
        calls = self.calls
        insn_max = self.insn_max

        # ---- 1. Decide: snapshot of the start-of-tick state ----
        sc = self._tmpl_code[:]
        se = self._tmpl_zero[:]
        for i in live:
            p = pos[i]
            sc[p] = col[i]
            se[p] = en[i]
        ctx = _TickCtx()
        ctx.tick = t
        ctx.w = self.W
        ctx.h = self.H
        ctx.sc = sc
        ctx.se = se
        ctx.offs = self.offs
        ctx.tts = self._tts
        ctx.self_type = self.self_type
        pop = self.pop
        total_pop = sum(pop)
        rnd = self.rng.getrandbits
        acts = []
        append = acts.append
        alt = self.order_by_alt
        saved = None if self.stun_keeps_memory else {}
        self._saved = saved
        for i in live:
            c = col[i]
            p = pos[i]
            age = t - born[i]
            if age > 255:
                age = 255
            m = mems[i]
            v = View(ctx, p, en[i], rnd(8), age, p % PW - 2, p // PW - 2, pop[c], total_pop - pop[c], c)
            if saved is not None:
                saved[i] = bytes(m)
            try:
                r = pols[c](v, m)
                a = r[0]
                n = r[1]
                k = n                     # count used for turn order
                if len(r) > 2:
                    if len(r) > 3:
                        raise ValueError('too many return values')
                    if alt:
                        k = r[2]
                        if type(k) is not int or k < 0:
                            raise ValueError('bad alt count')
            except Exception:
                self._fault(c, t, p, FAULT_CRASH, 0)
                continue
            finally:
                if len(m) != MEM_SIZE:   # only the first 64 bytes exist / persist
                    del m[MEM_SIZE:]
                    m.extend(bytes(MEM_SIZE - len(m)))
            if type(n) is not int or type(a) is not int or n < 0:
                self._fault(c, t, p, FAULT_CRASH, 0)
                continue
            if n > INSN_BUDGET:
                self._fault(c, t, p, FAULT_BUDGET, INSN_BUDGET + 1)
                continue
            insn_total[c] += n
            calls[c] += 1
            if n > insn_max[c]:
                insn_max[c] = n
            a &= 0xFF                     # only al is read as the action
            if not valid[a]:
                self._fault(c, t, p, FAULT_BAD_ACTION, None)
                continue
            if a != ACT_NOP:
                append((k, i, a))

        # ---- 2. Act: one pass, fewest instructions first, ties shuffled with the match RNG ----
        self.rng.shuffle(acts)
        acts.sort(key=_first)
        track = self.deltas is not None or self._idle_rng is not None
        if track:
            start = [(i, en[i]) for i in live]
            self._ev = ev = {}            # cell id -> events this tick (eat/feed/split/move, either side)
            self._fed = fedn = {}         # cell id -> times fed this tick
            self._rested = rested = set()
        self._act(t, acts)
        if self._idle_rng is not None:
            rr = self._idle_rng.random
            prob = self.idle_gain_prob
            for i, _ in start:
                if alive[i] and i not in ev and i not in rested and rr() < prob:
                    en[i] += 1

        # ---- 9. Tidy ----
        cap = ENERGY_MAX
        newlive = []
        pop = [0] * MAX_COLONIES
        esum = [0] * MAX_COLONIES
        for i in live:
            if alive[i]:
                e = en[i]
                if e > cap:
                    e = en[i] = cap
                newlive.append(i)
                c = col[i]
                pop[c] += 1
                esum[c] += e
            else:
                grid[pos[i]] = GRID_EMPTY
                mems[i] = None
        self.live = newlive
        self.pop = pop
        self.energy = esum
        if track:
            dl = self.deltas
            if dl is not None:
                hi = dl['idle']
                hf = dl['fed']
                for i, e0 in start:
                    if not alive[i]:
                        continue
                    k = ev.get(i, 0)
                    if k == 0:
                        h = hi
                    elif k == 1 and fedn.get(i) == 1:
                        h = hf
                    else:
                        continue
                    d = en[i] - e0
                    h[d] = h.get(d, 0) + 1
            self._ev = self._fed = self._rested = None

        # ---- end of match ----
        living = 0
        for c in range(MAX_COLONIES):
            if not self.present[c]:
                continue
            if pop[c] > 0:
                living += 1
            elif self.death_tick[c] is None:
                self.death_tick[c] = t
        self.tick = t + 1
        n_present = sum(self.present)
        if (self.tick >= self.max_ticks or living == 0 or (living == 1 and n_present > 1)):
            self.finished = True
        return not self.finished

    def _act(self, t, acts):
        """Apply the actions in turn order.  acts = [(insn, cell id, action)], already sorted."""
        grid = self.grid
        pos = self.c_pos
        col = self.c_col
        en = self.c_en
        alive = self.c_alive
        done = self.c_done
        dirs = self.dirs
        live = self.live
        stuns = self.stuns
        deaths = self.deaths
        capmid = self.cap_mid_tick
        cap = ENERGY_MAX
        split_ceil = self.split_ceil
        moves = self.moves
        feeds = self.feeds
        eats_enemy = self.eats_enemy
        eats_friend = self.eats_friend
        saved = self._saved
        bf = self.bite_first
        sh = self.split_energy
        ev = self._ev
        fedn = self._fed
        rested = self._rested
        bonus = self.feed_bonus
        races = self.races
        if bf is not None:
            seen = [0] * MAX_COLONIES      # successful eats so far this tick, per colony
            others = [tuple(o for o in range(MAX_COLONIES) if o != b) for b in range(MAX_COLONIES)]
        for n, i, a in acts:
            # dead (killed earlier this tick) or stunned (bitten before its turn): no turn
            if done[i] == t or not alive[i]:
                continue
            done[i] = t
            if a == ACT_REST:
                e = en[i] + REST_GAIN
                if capmid and e > cap:
                    e = cap
                en[i] = e
                if rested is not None:
                    rested.add(i)
                continue
            kind = a & 0xF0
            p = pos[i]
            tp = p + dirs[a & ACT_DIR_MASK]
            g = grid[tp]
            if kind == ACT_MOVE:
                # only a truly empty square: a corpse still holds its square until Tidy
                if g == GRID_EMPTY:
                    grid[p] = GRID_EMPTY
                    grid[tp] = i
                    pos[i] = tp
                    if races is not None:
                        self._race_fill(t, tp, col[i], 2, en[i])
                    moves[col[i]] += 1
                    if ev is not None:
                        ev[i] = ev.get(i, 0) + 1
            elif kind == ACT_EAT:
                if g >= 0 and alive[g]:
                    eg = en[g]
                    take = EAT_TAKE if eg > EAT_TAKE else eg
                    eg -= take
                    en[g] = eg
                    e = en[i] + take
                    if capmid and e > cap:
                        e = cap
                    en[i] = e
                    if ev is not None:
                        ev[i] = ev.get(i, 0) + 1
                        ev[g] = ev.get(g, 0) + 1
                    ci = col[i]
                    cg = col[g]
                    if cg == ci:
                        eats_friend[ci] += 1
                    else:
                        eats_enemy[ci] += 1
                    if bf is not None:
                        for o in others[ci]:
                            bf[o][ci] += seen[o]
                        seen[ci] += 1
                    if races is not None:
                        self._last_eater[g] = ci
                    if eg == 0:
                        alive[g] = False
                        deaths[cg] += 1
                        if races is not None:
                            self._race_death(t, g)
                    if done[g] != t:          # bitten before its turn: stunned
                        done[g] = t
                        stuns[cg] += 1
                        if saved is not None and g in saved:
                            self.c_mem[g][:] = saved[g]   # the call never took effect: drop its writes
            elif kind == ACT_FEED:
                if g >= 0 and alive[g]:
                    e = en[i]
                    give = FEED_AMOUNT if e > FEED_AMOUNT else e
                    e -= give
                    en[i] = e
                    eg = en[g] + give + (bonus if give else 0)
                    if capmid and eg > cap:
                        eg = cap
                    en[g] = eg
                    feeds[col[i]] += 1
                    if ev is not None:
                        ev[i] = ev.get(i, 0) + 1
                        ev[g] = ev.get(g, 0) + 1
                        fedn[g] = fedn.get(g, 0) + 1
                    if e == 0:
                        alive[i] = False
                        deaths[col[i]] += 1
                        if races is not None:
                            self._race_death(t, i)
            else:  # ACT_SPLIT
                e = en[i]
                if g == GRID_EMPTY and e >= SPLIT_MIN:
                    child = (e + 1) // 2 if split_ceil else e // 2
                    en[i] = e - child
                    c = col[i]
                    k = len(pos)
                    pos.append(tp)
                    col.append(c)
                    en.append(child)
                    self.c_born.append(t + 1)                 # VIEW_AGE 0 on its first tick
                    self.c_mem.append(bytearray(self.c_mem[i]))  # copy incl. this tick's writes
                    alive.append(True)
                    done.append(t)                            # takes no turn this tick
                    live.append(k)
                    grid[tp] = k
                    self.births[c] += 1
                    if races is not None:
                        self._race_fill(t, tp, c, 1, child)
                    if sh is not None:
                        sh[c][e] = sh[c].get(e, 0) + 1
                    if ev is not None:
                        ev[i] = ev.get(i, 0) + 1

    def _race_death(self, t, g):
        p = self.c_pos[g]
        mask = 0
        grid = self.grid
        alive = self.c_alive
        col = self.c_col
        for d in self.dirs:
            k = grid[p + d]
            if k >= 0 and alive[k]:
                mask |= 1 << col[k]
        self._race_pending[p] = (t, col[g], self._last_eater.pop(g, -1), mask)

    def _race_fill(self, t, p, c, kind, e):
        pr = self._race_pending.pop(p, None)
        if pr is not None:
            self.races.append((pr[0], pr[1], pr[2], pr[3], c, t - pr[0], kind, e))

    def race_rows(self):
        """Recorded races plus the squares still unfilled (fillCol -1, dt = ticks run since the death)."""
        if self.races is None:
            return None
        out = list(self.races)
        for pr in self._race_pending.values():
            out.append((pr[0], pr[1], pr[2], pr[3], -1, self.tick - pr[0], 0, -1))
        out.sort()
        return out

    def _fault(self, c, t, p, kind, insn):
        f = self.faults[c]
        f[kind] = f.get(kind, 0) + 1
        if insn is not None:
            self.insn_total[c] += insn
            self.calls[c] += 1
            if insn > self.insn_max[c]:
                self.insn_max[c] = insn
        if len(self.fault_log[c]) < FAULT_LOG_MAX:
            self.fault_log[c].append((t, p % self.PW - 2, p // self.PW - 2, kind))

    def run(self):
        while self.step():
            pass
        return self.ranking()

    # ---- result ----------------------------------------------------------------------------------
    def ranking(self):
        """Placement list (best first): dicts with colony, place, points and stats.

        Living colonies: population desc, total energy desc, total instructions asc.
        Dead colonies below, by death tick desc (lasted longer = better).  Remaining ties: lower colony.
        Points 3, 2, 1, 0 by placement (ASSUMPTION for matches with fewer than 4 colonies: the same
        list, top-down).
        """
        keys = []
        for c in range(MAX_COLONIES):
            if not self.present[c]:
                continue
            if self.pop[c] > 0:
                keys.append(((0, -self.pop[c], -self.energy[c], self.insn_total[c], c), c))
            else:
                dt = self.death_tick[c] if self.death_tick[c] is not None else -1
                keys.append(((1, -dt, c), c))
        keys.sort()
        points = (3, 2, 1, 0)
        out = []
        for place, (_, c) in enumerate(keys):
            calls = self.calls[c]
            out.append({
                'colony': c, 'place': place + 1, 'points': points[place],
                'alive': self.pop[c] > 0, 'pop': self.pop[c], 'energy': self.energy[c],
                'insn_total': self.insn_total[c],
                'avg_insn': (self.insn_total[c] / calls) if calls else 0.0,
                'max_insn': self.insn_max[c], 'calls': calls,
                'death_tick': self.death_tick[c], 'faults': dict(self.faults[c]),
                'births': self.births[c], 'deaths': self.deaths[c], 'stuns': self.stuns[c],
                'moves': self.moves[c], 'feeds': self.feeds[c], 'eats_enemy': self.eats_enemy[c],
                'eats_friend': self.eats_friend[c],
            })
        return out
