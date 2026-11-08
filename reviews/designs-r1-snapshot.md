# CellHack2 cell designs — round 1 draft (2026-11-07)

> **Update 2026-11-08 (docs re-review).** This is a historical record; its open questions are kept as written. A later full re-read of `docs/` settled several of them: every instruction counts, including taken jumps and `ret` (Reference p.3); energy is capped at 50 in the Tidy step (Rules p.1); feed gives 2 of the feeder's energy to any cell in that direction, so "fed +3" is feed 2 + rest 1, with no bonus (Rules p.1-2); a square freed by a death opens next tick, one freed by a move opens the same tick (Rules p.2); matches are deterministic from the seed (Rules p.3); SSE2 and SSE3 are available (Reference p.3); loops, the stack and `[rdx]` memory are allowed by the game. Ladder starts are not corners (replays; the Rules never say corners). See `architecture/overview.md` for the current summary.

Planning only. No code yet. Rules source: `docs/` (ruleset v9, ABI 4). Instruction counts below are
estimates that assume every executed instruction (including `ret` and taken jumps) counts as 1.

---------------------------------------------------------------------------------------------------
## 1. What the rules imply (shared analysis)

### 1.1 Facts and their consequences

1. **Score = population at the end.** Total energy and fewer total instructions are only tie-breaks.
   Population is bounded by squares held: 64x64 = 4096, about 1024 per colony on an even split.
   Every empty square inside your area at tick 3000 is a lost point.
2. **Splitting does not destroy energy**; it halves it between parent and child. Growth is limited by
   free squares and by cells reaching 5, not by an energy cost. The opening is a land grab.
3. **Rest (+1) is the only income, capped at 50.** In a packed interior nearly every cell sits at the
   cap, so its income is wasted. Interior energy is a large idle reserve that only matters if it
   reaches the border (feeding) or turns into splits.
4. **Initiative = fewest instructions in this call; a bite stuns a target that has not acted yet.**
   In a front-line duel the faster cell eats every tick and the slower cell never acts (stun-lock).
   The instruction count of the "enemy adjacent -> eat" path is the most important number in the
   program. Bots use < 20 instructions. Ties are random each tick.
5. **2 out vs 1 in.** A stun-locked front cell loses 2/tick and can only be kept alive by feeding.
   A friend can feed at most 2/tick, and a chain where every link feeds every tick has no income of
   its own (it runs on stored energy). Losing initiative on a long straight front is a slow loss;
   feeding delays it. **Geometry matters:** an enemy cell touching 2-3 of ours can stun only one per
   tick, the others eat it freely. Corners and salients are where kills happen.
6. **Eating a cell with <= 2 energy kills it**, and a child from a split at 5 has 2-3 energy.
   Never split a weak child next to an enemy (a free meal). Early-expansion frontier cells of every
   colony are one-bite kills: the window for raiding.
7. **Order resolves contested squares too.** Moves and splits into the same square, and
   feed-before-bite on a near-dead friend, are all decided by instruction counts. A square freed by a
   death is unusable until next tick; a square vacated by a move is usable later in the same tick.
   A bite lands on whatever is in the square at that moment, including a friend that just moved in.
8. **64 bytes of memory are inherited at birth.** The first cell can record its home corner (x, y at
   tick 0) and every descendant knows it; roles, modes and counters can be inherited.
9. **Free global information every call:** tick, POP_SELF, POP_ENEMY, x, y, W, H, colony slot.
   Phase changes (endgame, ahead/behind) cost 1-2 instructions and need no coordination.
10. **A split on the last ticks is +1 population for free.** Every design ends with a fill phase.
11. **Ladder = four-colony free-for-all including the open bots** (Hunter, Idle, Medic, Random,
    Walker). Weak colonies leave land unclaimed; expanding into all empty space, not just the home
    quadrant, pays. Points 3/2/1/0 by placement.
12. **A fault (crash, >1000 instructions, bad action) = no action that tick.** Every path must be
    bounded, must return a valid action, and must only touch mapped memory.
13. **Self-signalling exists only through what neighbours can see:** cell type and energy. Cells
    cannot read each other's memory. Energy gradients are the only "field" a colony can build.

### 1.2 Initiative tiers (the menu every design picks from)

| Front-path technique | Instr. | Notes |
|---|---|---|
| Static order check (`cmp byte [rdi+VIEW_CELLS+d], CELL_ENEMY` / `je`), 4 directions | 4 / 6 / 8 / 10 | Cost depends on which direction the enemy is in. No state. |
| SSE2 mask: `movdqu` 16 bytes from VIEW_CELLS+7 (covers indices 7, 11, 13, 17), `pcmpeqb`, `pmovmskb`, `and 0x451`, `jz`, table lookup by mask, `ret` | 7 flat | Also yields enemies at distance 2 in that window for free. |
| Mode dispatch: `movzx eax, byte [rdx+MODE]` + `jmp [table+rax*8]` | +2 on every path | Needed for any per-cell mode. Safe on zeroed memory (mode 0 = default). A 1-instruction `jmp [rdx]` faults on the root's first call, when memory is all zero. |
| Locked blind eat: dispatch -> `mov al, ACT_EAT+d` / `ret` | 4 | Never checks the target. Wastes ticks once the target dies; can bite a friend that moved in. Needs an exit rule. |
| Locked checked eat: dispatch -> `cmp` / `jne` / `mov` / `ret` | 6 | Falls through to the full logic when the target is gone. |
| Locked branchless "post": dispatch -> `movzx` cell type -> `mov al, [type_table_d + rax]` -> `ret` | 5 | Eat if enemy in direction d, else a fixed fallback (rest). Never leaves the mode by itself. |

The floor for any useful decision is about 4 (one branch plus `mov`/`ret`). Hunter-class code is
probably 5-10 on its eat path. A design that wants to win duels against tuned opponents needs 4-5.

### 1.3 Facts to verify in the sandbox (tuning, not structure)
- Split rounding: does the child get floor(e/2) or ceil(e/2)?
- Do `ret` and taken jumps count? Do `rep`-prefixed string instructions count once or per iteration?
- What register values are guaranteed at entry besides rdi/rsi/rdx/rsp (is rax zero)?
- Cell type reported at VIEW_CENTER (self).
- Exact start squares (true corners or inset?).
- Sandbox board size and tick limit (ladder: 64x64, 3000).
- Can energy above 50 mid-tick (before Tidy) be spent, e.g. a capped cell that is fed and then splits?

---------------------------------------------------------------------------------------------------
## 2. Shared kernel (all three designs)

- **Memory map (draft).** `[0]` mode byte (0 = default), `[1]` flags (bit 0 = initialised),
  `[2]` home corner (bit 0 = right half, bit 1 = bottom half), `[3]` role, `[4]` locked direction,
  `[5]` last action, `[6]` last energy, `[7]` small counters / initiative score, `[8..63]` per design.
- **Init:** if flags = 0 (only the root on tick 0, since children copy the parent), compute the home
  corner from x/y vs W/2, H/2 and set flags.
- **Check order:** (1) combat fast path, (2) endgame fill, (3) design-specific logic, (4) rest.
- **Opener:** tick 0, root has 10: split outward (away from home corner) -> 5/5.
- **Prey rule:** do not split into a square that has an enemy next to it unless the child gets
  >= K energy (draft K = 8, enough to survive a bite and act).
- **Endgame fill:** from tick END-20, split into any empty neighbour whenever e >= 5; in the last
  two ticks ignore the prey rule (a child that dies after the final count still counted).
  END comes from a constant (3000); verify the sandbox value.
- **Outward preference:** when choosing among empty squares, prefer the two directions away from
  the home corner, then the others.
- **Feed margin:** feed only when `my_e - target_e >= 4` (a smaller margin makes two cells feed each
  other back and forth).
- **Safety:** no loops without a fixed bound; all view indexing from constants or masked values;
  every exit sets `al` to a defined action.

---------------------------------------------------------------------------------------------------
## 3. Design A — "Bastion" (hold: dense land, fat border, feed the front)

**Bet.** Most games are decided by how much land is grabbed in the first ~200 ticks and by not
losing it afterwards. Fill every square, keep border cells fat, push idle interior energy outward.
Lowest complexity; it is the baseline the others must beat.

**Decision, in priority order**
1. Enemy adjacent -> eat. Static-order check (4-10 instr). If more than one enemy is adjacent, eat
   one with <= 2 first (a kill removes an attacker for good), else the first found.
2. Endgame fill (shared kernel).
3. Empty neighbour and e >= split threshold -> split (outward first; prey rule applies).
   Threshold 5 when no enemy is visible in the 5x5 view (land grab), 16 when one is (child >= 8).
4. Feed. If e >= 20 (or e = 50 anywhere) and a friend neighbour is poorer by >= 4, feed the poorest;
   friends that touch an enemy (visible in the 5x5) get priority. Deep capped cells feeding the
   poorest neighbour builds an energy gradient toward the border without any coordination.
5. Rest.

**Strengths.** Simple, few modes, no dispatch overhead, cheap common paths. Self-repairing (empty
squares inside get filled). Should crush the passive bots.
**Weaknesses.** No initiative edge over tuned opponents; on a straight front against a faster eater it
bleeds slowly. Never pushes into enemy land except by filling squares its border cells empty.
**Complexity.** Low (est. 150-250 lines).

---------------------------------------------------------------------------------------------------
## 4. Design B — "Tide" (adaptive: hold by default, push where it wins)

**Bet.** After the land grab the board is full and the remaining ~2800 ticks are attrition. The
colony that attacks only where it is locally stronger, and holds elsewhere, gains land without
paying for losing fights.

**Same as Bastion, plus:**
1. **Initiative sensing.** Each cell stores its last action and last energy. "I chose EAT and my
   energy went up by about 2" = I acted first. "My energy dropped and my action left no trace" =
   I was bitten and stunned (lost initiative). A per-cell score in memory is inherited by children,
   so what a front cell learns spreads along its lineage.
2. **Local strength.** Sum of friend energies minus enemy energies in the 5x5 (SSE2: masks with
   `pcmpeqb`, `pand` with VIEW_ENERGIES, `psadbw` to sum; roughly 10-14 instructions, slow path only).
3. **Push rule.** A border cell pushes when (strength advantage >= S) or (the target has <= 2) or
   (initiative score says we win): eat, and when the square frees, split into it with a fat child
   (>= 8). Second-row cells feed the pusher. Otherwise behave exactly like Bastion.
4. **Global modulation.** If POP_SELF < POP_ENEMY / 3 (below an even share) lower S (more pushes);
   if well ahead, raise S. From END-200 stop pushing and fatten the border.
5. **Losing initiative.** A front cell that keeps losing duels gets a richer feed priority and its
   neighbours stop splitting toward that enemy (don't feed the enemy fresh 2-energy cells).

**Strengths.** Takes land from weak neighbours (bots, slow coders) without suiciding into strong
ones. Uses information the other designs ignore.
**Weaknesses.** Slow path is long (only matters off the front). Sensing can be fooled (feeds and
bites in the same tick blur the energy delta). More parameters to tune.
**Complexity.** Medium (est. 300-450 lines).

---------------------------------------------------------------------------------------------------
## 5. Design C — "Reaper" (all-in aggression and initiative)

**Bet.** Initiative decides duels, and every colony is weakest during expansion. Win duels with a
4-instruction locked eat and raid the enemy's soft frontier before it hardens; take land by force.

1. **Locked combat.** On first contact the full logic sets mode = LOCK_d. Locked path: mode
   dispatch -> `mov al, ACT_EAT+d` -> `ret` (4 instr). Exit rule (pick in review): re-check every
   Nth tick via `VIEW_TICK` (+2 instr), or use the 6-instruction checked lock, or the 5-instruction
   branchless post. The lock is only worth having if it beats opponents' 5-10.
2. **Expansion biased toward enemies.** Same opener, but the outward preference points at the two
   adjacent enemy corners and the centre.
3. **Raiders.** From about tick 20-40, frontier cells with e >= 16 facing an enemy direction take
   role RAIDER: move toward the nearest enemy visible in the 5x5, else along a bearing to the
   nearest enemy corner; eat anything adjacent, prefer cells with <= 2 (one-bite kills); after a
   kill, split into the freed square if e >= 10 to leave a foothold behind.
4. **Pincers.** When an enemy is visible diagonally at distance 1-2, move so that two of ours touch it.
5. **Minimal logistics.** Feed only locked cells (they earn nothing while eating) and raiders.
6. **Fallback.** If POP_SELF falls well below POP_ENEMY / 3 (raids failing), switch the lineage to
   Bastion behaviour via the mode byte.

**Strengths.** Highest ceiling vs the bots and vs colonies with slow code; exploits the expansion
window; the lock wins duels outright against anything slower than 4.
**Weaknesses.** Raiders forgo rest income and feed the enemy if they die; a blind lock wastes ticks
after its target dies and can bite friends; dispatch adds +2 to every other path; coin flips against
equally fast opponents. Most bug-prone (many modes and transitions).
**Complexity.** High (est. 400-600 lines).

---------------------------------------------------------------------------------------------------
## 6. Comparison

| | A Bastion | B Tide | C Reaper |
|---|---|---|---|
| Posture | Hold | Hold, push where stronger | Attack |
| Front eat path | 4-10 (static order) | 4-10 (static order) | 4 locked (+2 on all other paths) |
| Logistics | Gradient feeding | Gradient feeding + feed pushers | Feed locked cells and raiders only |
| Uses memory for | home corner | home corner, initiative score, last action/energy | modes, roles, lock direction |
| Expected vs passive bots | Strong | Strong | Strongest |
| Expected vs tuned hunters | Slow bleed on lost duels | Avoids losing fights | Wins duels if faster; coin flips if equal |
| Main risk | Too passive | Mis-sensing, tuning | Wasted income, bugs |

---------------------------------------------------------------------------------------------------
## 7. Alternatives considered (not chosen; reviewers may argue for them)

- **Lattice.** Keep a fixed 20% hole pattern ((x + 2y) mod 5 == 0, a perfect code: each occupied
  square touches exactly one hole) for internal mobility, traps and an endgame bloom that fills the
  holes. Not chosen: moving cells keep breaking the pattern, traps only catch naive bots, and final
  population is at best equal to a packed colony.
- **Spore.** Early seed cells walk out (1 square/tick, faster than a splitting front) to plant
  extra nuclei, multiplying frontier length. Not chosen yet: seeds earn nothing while walking and
  their small nuclei meet enemy fronts weak. Could become a shared opener option if the land-grab
  speed turns out to dominate.
- **Turtle.** Small, compact, very fat territory. Not chosen: gives up land, and land is score.

---------------------------------------------------------------------------------------------------
## 8. Test plan (draft)
1. Site sandbox (vs Hunter, small board) for ground truth: fault log, instruction averages, replays;
   use it to settle section 1.3.
2. Optional local simulator: Python rules engine + Unicorn x86-64 emulation (count instructions with a
   code hook) + NASM. Re-create the five bots from their published source. Run four-colony matches
   at 64x64 / 3000 ticks; track population and territory over time, instructions per call, faults.
   Needs NASM and Unicorn installed (neither is present now).
3. Ladder: one design per slot.

---------------------------------------------------------------------------------------------------
## 9. Questions for reviewers
1. Is any rule misread above? Any rule detail that changes a design?
2. How does each design lose? Which opponent or map situation beats it?
3. Is the land grab or the 2800-tick attrition phase more decisive? What expansion policy is fastest?
4. Are the instruction counts right, and is there a cheaper front path than those in 1.2?
5. Is any design too complex for its payoff, or missing an obvious cheap win?
