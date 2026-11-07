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
                 place_start=True):
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
        self.rng = random.Random(seed)
        self.seed = seed

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

        if place_start:
            k = start_inset
            corners = ((k, k), (width - 1 - k, k), (k, height - 1 - k), (width - 1 - k, height - 1 - k))
            for c in range(MAX_COLONIES):
                if self.present[c]:
                    x, y = corners[c]
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
        for i in live:
            c = col[i]
            p = pos[i]
            age = t - born[i]
            if age > 255:
                age = 255
            m = mems[i]
            v = View(ctx, p, en[i], rnd(8), age, p % PW - 2, p // PW - 2, pop[c], total_pop - pop[c], c)
            try:
                a, n = pols[c](v, m)
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
                append((n, i, a))

        # ---- 2. Act: one pass, fewest instructions first, ties shuffled with the match RNG ----
        self.rng.shuffle(acts)
        acts.sort(key=_first)
        self._act(t, acts)

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
                    if eg == 0:
                        alive[g] = False
                        deaths[col[g]] += 1
                    if done[g] != t:          # bitten before its turn: stunned
                        done[g] = t
                        stuns[col[g]] += 1
            elif kind == ACT_FEED:
                if g >= 0 and alive[g]:
                    e = en[i]
                    give = FEED_AMOUNT if e > FEED_AMOUNT else e
                    e -= give
                    en[i] = e
                    eg = en[g] + give
                    if capmid and eg > cap:
                        eg = cap
                    en[g] = eg
                    if e == 0:
                        alive[i] = False
                        deaths[col[i]] += 1
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
            })
        return out
