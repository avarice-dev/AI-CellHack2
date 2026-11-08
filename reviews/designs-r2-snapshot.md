# CellHack2 cell designs — round 2 (2026-11-07)

> **Update 2026-11-08 (docs re-review).** This is a historical record; its open questions are kept as written. A later full re-read of `docs/` settled several of them: every instruction counts, including taken jumps and `ret` (Reference p.3); energy is capped at 50 in the Tidy step (Rules p.1); feed gives 2 of the feeder's energy to any cell in that direction, so "fed +3" is feed 2 + rest 1, with no bonus (Rules p.1-2); a square freed by a death opens next tick, one freed by a move opens the same tick (Rules p.2); matches are deterministic from the seed (Rules p.3); SSE2 and SSE3 are available (Reference p.3); loops, the stack and `[rdx]` memory are allowed by the game. Ladder starts are not corners (replays; the Rules never say corners). See `architecture/overview.md` for the current summary.

Planning only; no code. Spec: `docs/` (ruleset v9, ABI 4) and the bot sources in `docs/bots/`.
Round 1 draft: `reviews/designs-r1-snapshot.md`. Reviews and the decision on every suggestion:
`reviews/r1-*.md`, `reviews/decisions-r1.md`. Instruction counts include every executed instruction
(taken jumps and `ret` too, per the Reference: "The engine counts every instruction"); calibrate on the site.

**Changes from round 1.** A flat 6-instruction SSE2 front ("F6") shared by all designs; no home-corner init
and no mode dispatch on hot paths; eating counts as income; prey rule covers the parent; freed squares are
refilled next tick; raiders and energy-delta sensing dropped; the trio is now one shared kernel plus two
bets: B = expansion, C = initiative. Tide and Reaper are retired.

---------------------------------------------------------------------------------------------------
## 1. Game analysis

### 1.1 Facts and consequences
1. **Score.** Ladder points by placement (3/2/1/0); within a match, population at the end, then energy, then
   fewer total instructions. Optimise rank, not margin. Population is bounded by squares held (4096 total).
2. **Energy.** World income is REST (+1, capped at 50 at Tidy). For a cell, EAT is income too
   (+min(2, target)); eating an enemy is +2 for us and -2 for them. Splitting conserves energy, but each
   frontier step costs the new cell 3-4 ticks of rest to reach 5: energy reaching the frontier is the
   growth throttle.
3. **Initiative.** Fewest instructions acts first; a bite stuns a target that has not acted. A strictly faster
   front cell eats every tick and its target never acts. One faster neighbour is enough to stun. Different
   code rarely ties (6 vs 7 is 100/0). The front-path count is the most important number in the program.
4. **Attrition.** A stun-locked cell loses 2/tick and survives only on feeds (each friend feeds at most
   2/tick; a chain where every link feeds every tick runs on stored energy). A strictly faster colony wins a
   straight front in the long run; feeding only delays. With equal speed, geometry (k of ours on one enemy:
   it acts first with probability 1/(k+1)) and logistics decide.
5. **Fragility.** A cell with <= 2 dies to one bite. A split at 5 leaves parent and child at 2-3: both are
   free meals next to an enemy.
6. **Timing.** Decisions see a start-of-tick snapshot; actions hit the live board. A death-freed square
   opens next tick; a move-vacated square opens later the same tick. Two cells splitting/moving into the
   same empty square: the faster wins, the slower wastes its tick (no rest either).
7. **Memory.** 64 bytes, copied to the child at birth (assumed to include the parent's writes in the
   splitting call). A child knows it is new from VIEW_AGE == 0. Zero memory must mean "default".
8. **Free information** each call: tick, POP_SELF, POP_ENEMY, x, y, W, H, colony slot.
9. **End.** No tick-limit constant exists; 3000 is hard-coded. Last-tick births can be eaten the same tick;
   whether they count is unverified.
10. **Faults** = no action. SSE2/SSE3 only (no SSSE3/SSE4/popcnt/BMI); legacy-SSE memory operands must be
    16-byte aligned or every call faults. Tables must be fully filled (int3 padding read as an action is a
    bad_action fault; a zero jump-table entry jumps to address 0).

### 1.2 The bots (real source, `docs/bots/`)
| Bot | Behaviour | Instructions by path |
|---|---|---|
| Hunter | eat adjacent enemy (checks U,R,D,L), else split at e>=6 in a random direction, else rest | eat U 7, R 10, D 13, L 16; rest 17; split 20 |
| Medic | e>=15 and friend above: feed up; e>=6: split random; else rest | rest 6, split 9 or 13, feed 9 |
| Walker | e>=6: split random; else 50/50 rest or move random | split 7, rest 7, move 9 |
| Random | e<6 rest; else random move/split/eat/feed in a random direction | 4 / 14 |
| Idle | rest | 2 (one cell forever) |

Hunter, Medic and Walker try to split in a random direction even into occupied squares, so once packed
their cells with e>=6 never rest: their interiors stall at about 6 energy and earn nothing. Any front path
of 6 or less acts before Hunter in every direction. Idle (2) always acts before us; it still loses
(+1 rest against 2 bites per eater).

**Opponent model.** The bots are only the floor. Most ladder opponents are cells written by other people,
from lightly edited bot copies to heavily tuned code. Plan for: fronts at 6 instructions or fewer (F6-class,
static orders tuned to their corner, locks, blind eats), fast expanders, and feeders. A design that only
beats the bots has not been tested. The simulator needs "rival" reference policies of this kind (section 5).

### 1.3 Front-path menu
| Technique | Instr. | Notes |
|---|---|---|
| Static order DOWN, LEFT, UP, RIGHT (`cmp byte [rdi+VIEW_CELLS+d],2` / `je`) | 4/6/8/10 (miss 8) | Beats Hunter in every direction; loses to a flat 6 in two directions. |
| **F6**: `movdqu xmm0,[rdi+VIEW_CELLS+7]` / `pcmpeqb xmm0,[kEnemy]` / `pmovmskb eax,xmm0` / `jmp [fight_tbl+rax*8]` -> `mov al,ACT_EAT+d` / `ret` | 6 flat (miss 4) | kEnemy = 2 in lanes 0,4,6,10 (U,L,R,D), 0xFF elsewhere. 1106-entry jump table (8.8 KB), every entry filled. Multi-enemy masks can go to a longer handler. |
| F5: same but `mov al,[act_tbl+rax]` / `ret` | 5 flat | Eat-or-rest only; cannot grow. Yardstick. |
| Checked lock (C): `movsx rcx,byte [rdx]` / `cmp byte [rdi+rcx+100],2` / `jne .f6` / `mov al,[rcx+eat_tbl+K]` / `ret` | 5 locked; +3 on every other path | [rdx] holds (VIEW_CELLS+idx-100); zero memory points at unused view byte 100, documented zero, so it never matches. Self-checking, so a child inheriting it is harmless. |
| Blind lock: `or al,[rdx]` / `jz .f6` / `ret` | 3 locked; +2 elsewhere | Needs rax = 0 at entry (verify). No exit: eats an emptied square or a friend that refilled it forever. Not planned. |

### 1.4 What decides games (effort order)
1. Front-path count (decides every duel outright when unequal).
2. Land-grab speed (sets the borders; decisive against passive bots and when fronts are tied).
3. Logistics (decides tied fronts; delays losing ones).
4. Push and refill rules (turn kills into land).

### 1.5 Sandbox calibration checklist
Known-length calibration cells first (match page shows average/max instructions per call). Hunter's split
path is 20 if every instruction counts, yet the Rules say the bots use "fewer than 20": check whether taken
jumps or `ret` really count (it changes relative order only if taken jumps are excluded). Then: split
rounding for odd energy and whether energy is conserved; `rep` counting; rax/xmm values at entry; what
VIEW_CELLS[12] reports for self; whether memory persists after a stun or a fault; whether the child's memory
includes the parent's same-call writes; whether a split uses live or snapshot energy; whether POP counts
include newborns; last VIEW_TICK value and whether last-tick births count; whether energy above 50 mid-tick
can be spent; colony-slot-to-corner mapping and exact start squares; whether eating a friend stuns it.

---------------------------------------------------------------------------------------------------
## 2. Shared kernel K (all designs)

**Code shape.** One source with `%ifdef DESIGN_A/B/C`, Python-generated tables, flattened with `nasm -e`
for upload. Entry: [C only: lock prefix] -> F6 -> fight table -> slow path. Nothing on the F6 path writes
memory. No loops anywhere. Constants and tables after the code, `align 16`.

**Memory (zero = default).** [0] lock (C only), [1] birth direction (written by the parent before a split),
[2] role (B scouts), [3] flags, [4..63] design-specific. No home-corner byte: corner from VIEW_COLONY tables
if the slot-to-corner mapping is fixed, else from x/y on the slow path.

**Slow path, in priority order** (only reached when no enemy is adjacent):
1. **Multi-enemy handler** (from the fight table, not the slow path): kill (target <= 2) first, else the
   fixed direction order DOWN, LEFT, UP, RIGHT, so neighbouring cells on a diagonal front bite different
   enemies.
2. **Endgame fill.** tick >= 2980: split into any empty neighbour if e >= 5; prey rule off for the last two
   ticks. From tick ~2950 stop feeding so cells hold energy for the fill.
3. **Refill.** An empty neighbour that has an enemy next to it (a freed front square): split into it only if
   parent and child both keep >= 8; otherwise rest to get there (neighbours feed this cell, see 5).
4. **Grab.** No enemy in the 5x5: split at e >= 5 into an empty neighbour, outward first (away from the home
   corner), contested squares broken by parity ((x + y + tick) & 1 picks which of two candidates goes first).
   Prey rule: never leave parent or child < 8 on or next to a square that touches an enemy (25-bit enemy
   mask from two `pcmpeqb`/`pmovmskb`, ring masks, table).
5. **Feed.** Never from e <= 2, never to a target >= 49. Capped donors (e >= 49) feed the poorest friend with
   e <= donor - 3. Other donors with e >= 14 feed the poorest friend if the margin is >= 4. During the grab,
   donors with e >= 10 feed a friend that has an empty neighbour (frontier assist). "Poorest friend" routes
   energy to the front without any front-detection logic.
6. **Gap.** Enemy two squares away across an empty square: fill it only with a child >= 8.
7. **Rest.**

---------------------------------------------------------------------------------------------------
## 3. The three designs

### A — Bastion (kernel only: the control)
The kernel and nothing else. Fastest slow paths, fewest parameters, least to go wrong. F6 beats every bot's
eat path; kill-and-refill eats through stalled bot colonies on its own. Every other design must beat A in
the simulator to keep its slot. Estimated 200-300 lines plus generated tables.

### B — Spore (expansion bet)
Bet: the land grab sets the borders for the rest of the game, and MOVE (1 square/tick, free) is 3-4x faster
than a rest-and-split front (0.25-0.33 squares/tick).
1. **Scouts.** In the first ~20 ticks, 2-4 early cells with e >= 12 take role SCOUT (set by the parent via
   memory before the split; the parent clears its own copy next call). They walk outward along bearings
   toward the board centre and the two adjacent edge midpoints for 15-25 squares, then plant: become
   ordinary kernel cells and grow a nucleus. A scout that sees an enemy plants immediately.
2. **Stronger grab assist.** Donors from e >= 8 feed frontier friends during the grab.
3. **Push where strong (slow path, stateless).** Local strength = total - 2 x enemy energy in the 5x5
   (`psadbw`, 18-24 instructions). When strength >= S, cells one square behind the front feed the front and
   cells at distance 2 from an enemy create 2-on-1 contacts (split/move to touch the same enemy twice).
   S is lowered when POP_SELF < POP_ENEMY / 3 (below an even share) and raised when well ahead; no pushing
   after tick 2800.
Risk: scouts earn nothing while walking and their young nuclei meet enemy fronts weak. Estimated 350-450
lines.

### C — Lock (initiative bet)
Bet: serious ladder rivals will converge on a ~6-instruction front (F6-class), and a strictly faster
sustained duel wins everything over 2800 ticks.
1. **Checked lock** (1.3): 5 instructions while engaged; +3 on all other paths; the first contact tick costs
   10 (lock check miss + F6 + one store of the lock byte in the eat stub). The lock needs no exit logic: it
   checks its target every call and falls through to F6 when the target is gone.
2. Everything else is the kernel.
Measured head to head, C should beat A on every sustained front (5 < 6) and lose first-contact ticks
(10 > 6). Against Hunter both win. Keep C's slot only if the simulator shows it beats A, and replace it if
site data shows rivals are slower than 6 (then the lock buys nothing). Estimated A + 30 lines.

---------------------------------------------------------------------------------------------------
## 4. Comparison
| | A Bastion | B Spore | C Lock |
|---|---|---|---|
| Bet | Simplicity, kernel quality | Land grab decides | Initiative decides |
| Front path | F6 = 6 | F6 = 6 | 5 engaged, 10 first contact |
| Other paths | baseline | + scout/push logic | +3 everywhere |
| Wins against | bots | bots, slow expanders | F6-class rivals |
| Main risk | Ties with equal rivals | Scouts wasted | Tax with no gain vs slow rivals |

---------------------------------------------------------------------------------------------------
## 5. Simulator experiments (rules-only Python engine in `sim/`)
1. **Grab speed.** Split@5 alone vs + frontier feed (e>=10, e>=8) vs + scouts: squares held at ticks 50, 100,
   200 in a four-way mirror and against the bots. Decides B's slot and the kernel's feed thresholds.
2. **Front duel.** Straight 20-cell front, A (6) vs Hunter (7-16) and vs C (5), with and without logistics:
   rows lost per 100 ticks. Confirms the initiative model and C's value.
3. **Logistics.** Feed-rule variants: how long a stun-locked front cell survives, energy reaching depth 10.
4. **Eat-through.** A against a packed Hunter and Medic colony: squares gained per 100 ticks.
5. **Conveyor.** Fat interior cells walking to the front through holes (R14) vs feed chains only.
6. **Endgame.** Population gained by the fill rule.
7. **Full matches.** A/B/C against rival policies and bots in rotated four-colony mixes over many seeds;
   placement points.
8. **Rival policies** to build first (plausible strong human cells): R-F6 (F6 front + split@6 + rest),
   R-Static (static order tuned per corner, 4-6 on its front directions), R-Blind (3-instruction blind lock),
   R-Grab (fast expander with frontier feeding, no combat logic beyond eat), R-Feeder (Medic-style logistics
   + F6). Our designs are judged mainly against these, the bots are a sanity floor.

---------------------------------------------------------------------------------------------------
## 6. Rejected
- Tide (round 1 B): its sensing sat on the front path and it was 80% Bastion; sensing is noisy (X9).
- Reaper raiders (round 1 C): kill a few 2-3 energy cells, then die and feed the third and fourth colonies.
- Lattice: 20% holes mid-game; revisit only if experiment 5 shows a large logistics gain.
- Turtle: land is score.
- Mode dispatch on the hot path, the home-corner init, and the blind lock (see 1.3).
