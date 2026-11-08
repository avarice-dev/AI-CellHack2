# CellHack2 cell designs — round 3 (2026-11-08)

> **Update 2026-11-08 (docs re-review).** This is a historical record; its open questions are kept as written. A later full re-read of `docs/` settled several of them: every instruction counts, including taken jumps and `ret` (Reference p.3); energy is capped at 50 in the Tidy step (Rules p.1); feed gives 2 of the feeder's energy to any cell in that direction, so "fed +3" is feed 2 + rest 1, with no bonus (Rules p.1-2); a square freed by a death opens next tick, one freed by a move opens the same tick (Rules p.2); matches are deterministic from the seed (Rules p.3); SSE2 and SSE3 are available (Reference p.3); loops, the stack and `[rdx]` memory are allowed by the game. Ladder starts are not corners (replays; the Rules never say corners). See `architecture/overview.md` for the current summary.

Planning only. Round 3 is the first round built on real site data: `data/site-observations-2026-11-08.md`
(calibration cells, Sprint's ladder games, the decoded replay of match 98753, the leaderboard).
History: `reviews/designs-r1-snapshot.md`, `reviews/designs-r2-snapshot.md`, the reviews in `reviews/`,
and every decision in `reviews/decisions-r1.md` (round 1 and the reviewer's F1-F20).

**Names** (2026-11-08, user's choice): cells are named from `docs/cell_names.txt` (Stellaris names), matched to
behaviour. Dogma = the slot formerly called Hold (feeds its front, never gives ground); Contagion = formerly Spore
(scouts, spreads fast); Scourge = formerly Breach (kill, refill, keep eating forward). Our ladder cell Sprint is called
Avarice in the docs (eats greedily, never feeds); its ladder name and `cells/sprint.asm` stay Sprint. The simulator
may still use the old names in code.

**What changed since round 2, and why**
1. Starts are random, not corners. All corner, home and "outward from the corner" logic is replaced by an
   origin each colony records for itself (2.3).
2. The best rivals bite in 5 instructions or fewer. Our 6 (Sprint) lost almost every same-tick bite to
   Brawler (63 of 88183). The lock is no longer an option: every design has one (2.1).
3. The winners feed about 10 times per bite. Sprint never fed; its interior idled near 50 energy while its
   front was eaten. Feeding the front is core behaviour (2.4).
4. The slots are three settings of one kernel, chosen to differ where the simulator and the ladder must
   decide: lock type, grab policy and feeding depth (section 3).

---------------------------------------------------------------------------------------------------
## 1. Facts this round rests on

### 1.1 Verified on the site (2026-11-08)
| Fact | Evidence |
|---|---|
| Every executed instruction counts, incl. taken jumps and `ret` | calib-a 2 (2); Walker max 9 |
| rax = 0 at entry | calib-c 4 (4), no faults |
| `rep` counts per iteration + 1 | calib-d 105 |
| Ties between living colonies go to fewer total instructions | sandbox 98751 |
| Start positions are random squares | replay 98753 keyframe 0 |
| Events in a replay are logged in turn order | Sprint never eats after its own split in a tick |
| Saving a cell through the site form ladders it at once | cell 148 |
| Local Unicorn counts equal the server's | calib a, c, d |

### 1.2 Rivals (replay of 98753; leaderboard of 2026-11-08)
- **Brawler** (Striker, rated ~1230-1350 across versions): bites in <= 5, feeds ~11 times per eat, colony
  mean energy ~11, never moves. Held 838 cells to the end against AtomPush.
- **AtomPush** (HammerSpb, #2, wins 77%): bites below 6 on ~85% of contacts, feeds ~10 per eat, colony
  fat (mean ~48 from tick 500), grows faster than split-at-5 (386 vs 253 cells at tick 50).
- The field is small: ~20 active cells, ~10 players, 4 bots. HammerSpb's two cells are the target.
- Averages on match pages (35-90 per call for top cells) say nothing about front paths. Relative bite
  speed is measured from replay event order instead (data file, "Replays").

### 1.3 Still unknown (sim keeps both cases where it matters)
1. Do memory writes persist when a cell is stunned? Decides whether a lock set on the first-contact tick
   survives being bitten first. Sim flag.
2. Does a child's memory include the parent's same-call writes? Matters only for tick-0 data; the origin
   rule (2.3) works either way.
3. Exact rival bite counts: 3 (blind lock) or 5 (checked lock). Our first 5-lock cell on the ladder
   answers it: equal counts interleave in the event order, a 3 always goes first.
4. Start-position distribution (minimum distance, edges). Read from more replays' keyframe 0.
5. Split rounding for odd energy. Readable from replay births versus keyframes.

---------------------------------------------------------------------------------------------------
## 2. Shared kernel K

### 2.1 Front: locks (5 instructions engaged)
Both forms use the VIEW_W sentinel (review F14): zero memory points the check at VIEW_W's low byte, which
is 64 on the ladder and 16 in the sandbox, never a cell type. Lock byte `[rdx]` = VIEW_CELLS + idx - 12,
so UP 27, LEFT 31, RIGHT 33, DOWN 37.

**Checked lock (Dogma, Contagion).**
```
movsx  rcx, byte [rdx]
cmp    byte [rdi+rcx+12], CELL_ENEMY   ; unlocked: reads VIEW_W
jne    .f6
mov    al, [abs eat_tbl+rcx]           ; 38-byte table, EAT+d at 27/31/33/37
ret                                    ; 5 engaged; +3 on every other path
```
Pre-arming (slow path, no extra cost on the hot path): a cell that sees an enemy two squares away in a
straight line (view idx 2, 10, 14, 22) with the square between empty sets its lock toward that square.
When the enemy or its child steps in, the first bite is already 5. A pre-armed checked lock pointing at
an empty square just falls through (+3), so it is harmless.

**Post lock (Scourge).** The reviewer's form with the decision-r1 corrections:
```
movzx  ecx, byte [rdx]                ; 0 = unlocked
movzx  eax, byte [rdi+rcx+12]         ; target type, or VIEW_W when unlocked
add    al,  [abs post_tbl+rcx+rax*8]  ; (action - type) & 0xFF, or (-type) & 0xFF = "run full path"
jz     .full
ret                                   ; 5 engaged: EAT on ENEMY, SPLIT on EMPTY (refill); +4 elsewhere
```
`post_tbl` is 2041 bytes: index 8k (k = 4..255) holds (-k)&0xFF for any board width; locked indices are
odd. FRIEND and WALL fall through, and the slow path then clears the lock. Two costs: no pre-arming (a
pre-armed post lock would split toward the enemy blindly), and a refill at e < 5 wastes the tick. The
gain: a freed square is refilled at 5, and the child inherits the lock pointing at the next enemy row
(a breach column).

**F6 below the lock** (unchanged, Sprint's code): 6 on a bite plus the lock store (7), miss 4.
Multi-enemy choice is encoded in the fight table at no cost: two enemies D, L, U, R order; three enemies
bite opposite the friend side; four enemies any.

| Path | Checked (Dogma, Contagion) | Post (Scourge) |
|---|---|---|
| Engaged bite | 5 | 5 |
| First contact, pre-armed | 5 | n/a |
| First contact, not armed | 10 | 11 |
| Refill of a freed square | slow path, ~20 | 5 |
| Every other path | +3 | +4 |

Against a rival at 5 we tie (coin flip per tick, decided by feeding). Against a blind 3 we lose every
contact; a 3 cannot exit and bites anything that enters its square, which E6 must price before we decide
whether to answer with our own blind lock.

### 2.2 Memory layout (zero = default)
`[0]` lock, `[1]` flags (bit 0 = origin set, bit 1 = scout), `[2]` origin x, `[3]` origin y,
`[4]` scout bearing, `[5]` scout steps left, `[6..63]` spare. The lock byte stays across splits
(review F12); the slow path clears it when its target is not an enemy.

### 2.3 Origin instead of a corner
Slow path: if flag bit 0 is clear, store my x, y as origin and set the bit. The root does this on tick 0.
A child that missed it (if memory is copied before the parent's writes) takes its own birth square, one
step off, which is harmless. "Outward" = the directions that increase distance from the origin, the
longer axis first.

### 2.4 Feeding (defence)
Stateless diffusion, decided on the slow path. Front cells (an enemy adjacent) never reach it.
1. Never feed from e <= 4. Never feed a target >= 47.
2. Capped donors (e >= 47) feed the poorest friend neighbour if the margin is >= 2.
3. Other donors with e >= D feed the poorest friend neighbour if the margin is >= 4.
4. Grab assist: during the grab (no enemy in the 5x5), donors with e >= G feed a friend neighbour that
   has e < 5 and an empty neighbour.
D is the main design parameter: Brawler-like deep feeding (D ~ 6, colony mean ~11) versus
AtomPush-like fat reserves (D ~ 20, mean ~45). E1 and E7 decide.

### 2.5 Growth
- Split at e >= 5 into an empty neighbour, outward directions first.
- Prey rule: with an enemy in the 5x5, split only if the child gets >= 8 (parent e >= 16). Exception:
  Scourge's post-lock refill.
- Scouts (parameter S, 0-4): the root's early children with e >= 12 get the scout flag and a bearing
  (one outward axis each). A scout MOVEs along its bearing for up to L squares (parameter, ~15), stops on
  seeing an enemy in its 5x5 or when blocked, then clears the flag and grows as a normal cell.

### 2.6 Endgame
Stop long-range feeding from tick 2950; fill every empty neighbour from 2980; in the last two ticks a child
next to an enemy only if it gets >= 3 (a newborn can be bitten in its birth tick).

### 2.7 Code rules (unchanged from round 2 and the review)
SSE constants `align 16`; unaligned windows via `movdqu`; every table entry filled; `[abs table+reg*8]`;
generated tables with `times`; no org/bits/section/%include; no loops; nothing on the hot path writes
memory except the lock store on the first bite; check ABI_VERSION = 4 at build time.

---------------------------------------------------------------------------------------------------
## 3. The three slots

| | Dogma | Contagion | Scourge |
|---|---|---|---|
| Bet | Fronts freeze; defence and land at freeze time decide | The grab decides | Kills convert into land |
| Lock | checked + pre-arm | checked + pre-arm | post (refill at 5) |
| Feeding D (donor floor) | 6 (deep, Brawler-like) | 12 | 8, locked cells first |
| Grab assist G | 12 | 8 | 12 |
| Scouts S | 0 | 4 | 0 |
| Prey rule | child >= 8 near enemies | child >= 8 | child >= 8, except lock refills |

**Dogma.** Every front contact is 5 from the first tick; deep feeding keeps front cells topped up. Loses
least against a 5-rival; gains least against weak ones.

**Contagion.** Four scouts along the outward axes, strong grab assist. With random starts, a colony that
starts near an edge has fewer directions to grow; scouts move the growth front away from neighbours early.

**Scourge.** Post lock: a kill is followed by a refill at 5 and the child keeps eating forward. Pays off
against rivals that are slower than 5 or that feed thinly; risks wasted ticks on refills below 5 energy.

All three share the endgame, origin, memory layout, multi-enemy table and code rules.

---------------------------------------------------------------------------------------------------
## 4. Simulator plan (rules-only engine in `sim/`)
Engine updates in progress: random starts, a "memory persists when stunned" flag, rival policies
(R-Lock5 Brawler-like, R-Blind3, R-FatGrab AtomPush-like), a parallel experiment runner and replay-style
statistics, checked against the real match 98753.

Experiments, each with the decision it changes:
| # | Question | Setup | Changes |
|---|---|---|---|
| E1 | How much feeding does a front need? | Dogma with D = 4/6/10/20 vs R-Lock5 and R-FatGrab, 4-way, random starts | D per slot |
| E2 | Do scouts and grab assist pay with random starts? | Contagion with S = 0/2/4, G = 6/8/12, mirrors and vs rivals | Contagion's slot; S, G |
| E3 | Checked + pre-arm vs post lock | Dogma vs Scourge head to head and vs rivals | which lock goes into the other slots |
| E4 | Multi-enemy table vs kill-first handler | breach and salient setups | keep table at 6 |
| E5 | Does it matter if stunned writes are lost? | E3 with the memory flag flipped | lock design robustness |
| E6 | How bad is a blind-3 rival? | our designs vs R-Blind3 | whether to build our own blind lock |
| E7 | Fat reserve vs deep feeding | D sweep vs each rival type | D defaults |
| E8 | Endgame constants | stop-feed 2900/2950/2990, fill 2960/2980/2995 | constants |
| E9 | Ranking of the trio | each slot vs 3 draws from {rivals, Sprint, bots}, 50 seeds, rotated | which three go on the ladder |
Validation before trusting E1-E9: Sprint + R-Lock5 + R-FatGrab + Walker should look like match 98753
(Sprint wiped out by ~1500, rivals' eat/feed ratios ~1:10).

---------------------------------------------------------------------------------------------------
## 5. Ladder plan
- Sprint stays on the ladder to collect more games; analyse its replays after more games (user, 2026-11-08).
- The first round 3 cell on the ladder doubles as a probe: its bite order against Brawler and AtomPush
  shows whether they are at 5 (interleaved) or 3 (always first).
- Nothing goes on the ladder without the user's approval. New cells are created by the scripted POST
  that does not ladder them, then tested in the Sandbox.

---------------------------------------------------------------------------------------------------
## 6. Rejected or retired
- F6 without a lock: loses every contact to the top cells.
- Corner, home and colony-slot direction logic: starts are random.
- Tide, Reaper raiders, Lattice, Turtle: as in round 2.
- A pure control slot: the simulator plays that role.
