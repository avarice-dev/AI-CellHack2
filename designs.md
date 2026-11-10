# CellHack2 cell designs — round 4 (2026-11-08)

The current plan is section 11. Earlier sections are history where a pointer says so.

Planning only. Round 4 rests on both ladder data pulls (`data/ladder-data-2-2026-11-08.md` is the main source,
991 matches and 36 decoded replays), the site calibrations (`data/site-observations-2026-11-08.md`), the reviewer's
round 3 review (`reviews/r3-review.md`) and the lead's decisions on its G1-G20 (end of `reviews/decisions-r1.md`).
History: `reviews/designs-r1..r3-snapshot.md`.

**Names** (user's choice): cells are named from `docs/cell_names.txt` (Stellaris names), matched to behaviour.
Avarice = our first ladder cell, named Sprint until 2026-11-08 (eats greedily, never feeds). `cells/sprint.asm`, the code and stored match data keep the old name.
Covetous = Avarice's quick successor (on the ladder since 2026-11-08). Scourge, Contagion = the next two cells.
Ladder now (2026-11-08 22:42 UTC-06, `data/site-checks.md`): Contagion (1st), Schism (2nd), Complacency (3rd). Round 7 review: section 10. Current plan: section 11. Covetous, Scourge and Avarice are retired from the ladder.
Doctrine = a later feeding-depth variant. Dogma (formerly Hold) is retired. The sim may use old names in code.
Round 5 (section 8): Woe, Conceit, Endemic = VEX variants of Scourge, Covetous, Contagion (same decisions, fewer instructions).

**What changed since round 3, and why**
1. Pull 2 overturned "land is decided by t300-500": only 2 of 36 replays are frozen by t500; median freeze 2076.
   Late conversion of land matters as much as the grab.
2. A flat 5-instruction bite with no memory exists (Covetous, verified on the site): `or al,[bite_tbl+rcx]` with
   rax = 0 at entry, then `jnz EXIT_ADDR`. This supersedes every lock form for the bite (G3 asked for the post
   lock; its 5 is now free without memory, its first contact 11 was worse).
3. Avarice loses to HammerSpb on the refill race, not bite order (G2): it kills thousands of AtomPush cells and
   gains no land, because AtomPush refills freed squares faster (split path <= 20, children 5-7). A fast refill of
   freed front squares is the kernel's main new feature.
4. Deep pumps (interior ~6-10) are the field's losing economy (G1): Dogma is dropped. Feeding comes from capped
   cells only, plus a moderate donor floor D (12-16).
5. The "+3 on feed" and "+1 idle" are feed 2 + rest 1 and rest, which replays do not log (G4). Income = cells
   below the cap that rest. Energy above ~50 is wasted.

---------------------------------------------------------------------------------------------------
> **Docs re-review (2026-11-08).** A full re-read of `docs/` settled several points this file once marked open or inferred: every instruction counts, including taken jumps and `ret` (Reference p.3); the cap is applied at Tidy (Rules p.1); feed gives 2 of the feeder's energy to any cell in that direction, friend or enemy, so "fed +3" is feed 2 + rest 1 (Rules p.1-2); a square freed by a death opens next tick, one freed by a move opens the same tick (Rules p.2); matches are deterministic from the seed (Rules p.3); SSE2 and SSE3 are available (Reference p.3); the stack and `[rdx]` memory are allowed, so "no loops / no stack / no memory writes" are this project's speed rules, not game rules. See `architecture/overview.md` and `architecture/cell-assembly.md`.

## 1. Facts this round rests on

### 1.1 Verified on the site or in every replay
| Fact | Evidence |
|---|---|
| Every executed instruction counts, incl. taken jumps and `ret` | calib-a 2 (2); Walker max 9 |
| A call may end with `jmp`/`jcc EXIT_ADDR` instead of `ret` (1 instruction) | calib-e, Sandbox 99887 |
| rax = 0 at entry; `rep` counts per iteration + 1 | calib-c, calib-d |
| Within a tick cells act in instruction-count order, across colonies | every replay (pull 2 sec. 6) |
| Split: child floor(e/2), parent the rest; eat moves 2 (1 if target has 1); feed moves 2 | pull 2 sec. 6 |
| Cells cap near 50; bites by a capped eater gain nothing (66% of all bites) | pull 2 sec. 6, G4 |
| One start cell per colony at energy 10, on a random square (median 10 from an edge; closest pair median 18, min 8) | 144 starts |
| No diagonal eats; 14 of 36 matches end early at "last colony standing" | replays |
| Saving through the site form ladders a cell; a scripted POST does not (30 s between creations, else HTTP 429) | site notes |

### 1.2 Rivals (pull 2 sections 3-4)
- Every strong rival bites at ~4 in ONE fixed direction, maybe ~6 in a second, >= 8 in the rest; orders never change:
  Aegis U; Bouncer D (R 6); Noob+, Noob++ D; AtomCrasher, AtomPush R (L 6); Brawler, Brawler v2 U (L 6); rooby U (R 6).
- HammerSpb (AtomCrasher 77% wins, AtomPush 73%): fat colonies (interior ~46-47), no moves, splits spread out,
  refill freed squares fast with 5-7-energy children. AtomCrasher feeds ~6 per eat, AtomPush 4-300 by match.
- Pump cells (Bouncer, Brawler v2, Aegis, Noob+): thin interior 9-20, fat front ~28-38, 30-110 feeds per eat;
  they cause most of HammerSpb's 19% upsets by numbers (2000-2500 cells at t200).
- The grab matters: the t200 leader wins 22/36, the t500 leader 28/36; contact comes around tick 37 (G8).
- Direction luck is worth ~16 points of win rate, so judge a cell on >= 50 games (G11).

### 1.3 Still unknown
1. Is a rival's "6" direction 5, 6 or 7? Covetous answers it: its 5 bites first ~100% if the rival is 6, ~50% if 5.
2. Does memory persist when a cell is stunned? Matters only if a design uses memory on the front. Docs re-review 2026-11-08: implied yes (Rules p.1: step 1 Decide calls every cell before step 2 Act, so a cell's writes are done before any bite). Not stated outright; a Sandbox cell would confirm.
3. Resolved by replay mining: an event-free cell below 50 gains +1 in 95-99% of ticks, at 50 never. Income = resting cells below the cap.
4. Resolved by the docs (re-review 2026-11-08): energy is capped at 50 in step 9, Tidy (Rules p.1), so mid-tick 52-56 is expected.

---------------------------------------------------------------------------------------------------
## 2. Shared kernel K

### 2.1 Bite: F5 (Covetous form)
```
movdqu   xmm0, [rdi+VIEW_CELLS+VIEW_UP]
pcmpeqb  xmm0, [kEnemy]
pmovmskb ecx, xmm0
or       al, [abs bite_tbl+rcx]   ; rax = 0 at entry; ZF set = no adjacent enemy
jnz      EXIT_ADDR                ; 5 in every direction, no memory
```
Beats every rival's second direction (6) and every slow side (>= 8); loses only to a rival's single 4. Multi-enemy
choice is in the table (two or four enemies D, L, U, R; three: opposite the free side). The miss costs 5.

### 2.2 Refill: retake freed front squares fast (the new core feature)
A freed front square is an empty orthogonal neighbour that an enemy can reach next tick: one with an enemy in the
square beyond it or beside it (5x5 view). Stateless: no memory, so the stun question does not matter.
- Placed first on the slow path, right after the F5 miss. Replay mining (data/replay-mining-2026-11-08.md): refills
  always land on the NEXT tick, so the race is decided purely by turn order in that tick, i.e. by the refill path's
  instruction count. Avarice (split path 19-21) won 0.5% of contested squares vs AtomPush and 3.6% vs AtomCrasher;
  AtomPush wins 78% of all its contested races. So: make the refill path as short as possible (target <= 10, and
  measure AtomPush's actual refill cost from the event order before fixing the number).
- Child size: refill only when the child gets >= R energy (parent >= 2R). Default R = 6 (AtomPush's children are
  5-7); experiment E1 sweeps R in {3, 6, 8}. A refill from a 50 gives 25, two productive eaters (G10).
- Fallback if the stateless check cannot reach ~12: the post lock of round 3 (memory, refill at 5), at the cost of a
  lock store on the bite path (bite 6).

### 2.3 Feeding (from capped cells, G5)
1. Never feed from e <= 4; never feed a target >= 47 (Aegis wastes 34% of its feeds on full cells).
2. Capped donors (e >= 47, nothing to gain by resting) feed the poorest friend neighbour at margin >= 2.
3. Other donors with e >= D feed the poorest friend neighbour at margin >= 4. D in {12, 16} (E2).
4. Front cells never reach the feeding code (the bite or refill takes the tick).
Covetous already does rule 2 alone; it is the baseline for E2.

### 2.4 Growth
- Split at e >= 5 into an empty neighbour; the plain split path stays <= ~15 instructions and comes before the
  feeding code (G12): Avarice's late gains came from re-occupying dead colonies' squares fast.
- Prey rule: with an enemy in the 5x5, split only if the child gets >= 8, except refills (2.2).
- Grab assist (Contagion): during the grab (no enemy in the 5x5), donors with e >= G = 8 feed a friend
  neighbour with e < 5 that has an empty neighbour.
- Scouts (Contagion only): S <= 2, only from starts within 10 squares of an edge, along the longest free axis
  (G9; S = 4 was a corner-board artefact: contact comes at tick ~37). A scout MOVEs up to ~10 squares, stops on
  seeing an enemy or when blocked, then grows normally. Needs memory: origin and scout bearing.

### 2.5 Endgame
Stop long-range feeding from tick 2950; fill every empty neighbour from 2980; in the last two ticks a child next
to an enemy only if it gets >= 3 (a newborn can be bitten in its birth tick).

### 2.6 Memory (only Contagion uses it)
`[1]` flags (bit 0 origin set, bit 1 scout), `[2]` origin x, `[3]` origin y, `[4]` scout bearing, `[5]` steps left.
Nothing on the bite or refill paths reads or writes memory.

### 2.7 Code rules
SSE constants `align 16`; unaligned windows via `movdqu`; every table entry filled; `[abs table+reg*8]`;
generated tables with `times`; no org/bits/section/%include; no loops; check ABI_VERSION = 4 at build time;
cells/check_cells.py (NASM build, alignment map, Unicorn differential test vs sim/cells_ref.py) must pass.

---------------------------------------------------------------------------------------------------
## 3. The cells

| | Covetous (on ladder) | Scourge (next) | Contagion | Doctrine (later) |
|---|---|---|---|---|
| Bet | Faster bite is enough | Kills convert into land | The grab decides | Feeding depth |
| Bite | F5 | F5 | F5 | F5 |
| Refill (2.2) | no | yes, R = 6 | yes, R = 6 | as the better of the two |
| Feeding | capped donors only | capped + D = 16 | capped + D = 12 | D = 8 or 20 |
| Grab assist / scouts | no / no | no / no | G = 8 / S <= 2 | as parent |

**Covetous** is the interim data collector: F5 + capped feeding, otherwise Avarice. Its ladder record against
Avarice's measures what the bite alone is worth, and it probes the rivals' "6" directions (1.3.1).

**Scourge** is the next cell: Covetous plus the refill and D = 16. It targets HammerSpb directly (the refill race).

**Contagion** adds the grab tools to Scourge's kernel.

**Ladder slots (3)** (plan at round 4; current ladder: `data/site-checks.md`; current plan: section 11): Avarice and Covetous now. Scourge takes the third slot. When Contagion is ready, it replaces the
weakest of the four by then, and only after each has >= 50 games (G11). Every ladder change needs the user's approval.

---------------------------------------------------------------------------------------------------
## 4. Experiments (simulator; max 4 of 6 cores, below-normal priority, run as background batches)
The simulator's rival models are being refitted to pull 2's fingerprints (pump rivals were too fat, the late
game too slow). Trust E1-E4 only after that validation rerun. (Current validation state: 10.6.)
| # | Question | Setup | Changes |
|---|---|---|---|
| E1 | Refill race (G13) | refill R in {3, 6, 8} vs no refill, against the fat AtomPush-like rival | Scourge's R; squares gained per 100 ticks after first kill |
| E2 | Feeding depth (G14) | D in {8, 12, 16, 20} with capped donors, vs fat, pump and flat-6 rivals | D for Scourge, Contagion, Doctrine |
| E3 | Grab (G15) | G in {8, 12}, S in {0, 2}, measured start distribution; targets 300-400 / 700-1400 / 1300-2300 at t50/100/200 | Contagion |
| E4 | Counter-moves (G16) | a blind-3 rival; a rival with a 4-instruction refill in its fast direction | whether we need a faster answer |
Deferred: harvesting (G17: a second-row cell eating its own capped front cell); only as an experiment.

---------------------------------------------------------------------------------------------------
## 5. Data plan
- Covetous's first ~50 games: win rate and head-to-heads vs Avarice's (scheduled check), and its bite-first share in
  each rival's "6" direction (1.3.1), from one or two chosen replays only.
- Offline mining of the 35 stored replays: done (data/replay-mining-2026-11-08.md, tools/pull2/mine.py, a pure-Python decoder).
- Watch the leaderboard (small page) for rival version changes before fetching anything large. Fetch at the pace in "Pacing rules for the site" (architecture/data-pulls.md).

---------------------------------------------------------------------------------------------------
## 6. Rejected or retired
- Dogma and deep feeding (D ~ 6): losing economy in pull 2 (G1).
- Checked lock and pre-arming: refill at ~20 loses the race (G3).
- Post lock as the bite: F5 gives the same 5 without memory; kept only as the refill fallback (2.2).
- Scouts S = 4 and corner logic: starts are random and contact comes early (G9).
- Avarice's F6 as the base: F5 replaces it in every new cell.
- Tide, Reaper raiders, Lattice, Turtle, a pure control slot: as in rounds 2-3.

---------------------------------------------------------------------------------------------------
## 7. Exploratory cells (planner brainstorm 2026-11-08; ranked by value per effort; none built yet)
1. **Pestilence** (S, fits K): refill a freed square by MOVE with a fat front cell (>= 20), backfill its old square
   from the interior by split. Carries 30-50 energy forward in one action; nobody refills by move (0% in mining).
   Only pays once our refill wins the race (rides on Scourge). Guard: move only if the vacated square has no enemy
   neighbour. Test: E1 variant, squares held 10 / 50 ticks after capture.
2. **Conviction** (M, new architecture): a queue of up to 7 planned actions in one memory qword, executed in 3
   instructions (`shr qword [rdx],8 / mov al,[rdx] / jnz EXIT_ADDR`). A queued bite beats every rival's fast side
   (4); queued refills beat any rival refill. Est. contact-tick wins 75% -> ~87%. Risks: stale plans (eating empty
   squares or own children), +3 on every unqueued path, child may inherit the queue. Light version: queue after
   the F5 miss (bite 5, queued refill 8) fits K. Test: Unicorn count, then sim vs fixed-fast-direction rivals.
3. **Anxiety** (S-M, fits K): a scout settles fat in a left corner (preferably bottom-left), where no rival is fast
   (no rival is fast LEFT; only Bouncer/Noob+/Noob++ are fast DOWN). Insurance for last-colony-standing endings
   (14/36). Est. +0.1-0.15 points per game. Depends on rivals' LEFT being 6 (Covetous probe) and cap at Tidy.
4. **Abasement** (S, fits K): read the enemy two squares out; fat enemy (46-50, HammerSpb/rooby) -> hold the line, no
   cheap contested refills; thin enemy (9-20, pumps) -> push hard. Aims for a safe 2nd vs HammerSpb.
5. **Misfortune** (S, fits K): census switch from VIEW_POP_SELF / VIEW_POP_ENEMY; below ~15% share after t500 the
   whole colony goes to survival mode. Test: replay stat on Avarice's 17 replays.
6. **Famine** (S): harvesting (G17); low value for a fat-interior kernel, better in a pump variant.
7. **Bane** (M): notch traps that bait AtomPush's fixed refill; weak (energy-only, AtomPush banks ~158k).
Dropped: kill-order tricks, staircase fronts, a stateless 4-bite, a 2-instruction blind lock, hidden channels,
parity signalling. From the Rules (docs re-review 2026-11-08): the cap is applied at Tidy (stated, Rules p.1 step 9);
memory writes happen in Decide, before actions, so they survive a stun (implied by the step order, not stated).
Open: rivals' LEFT 6 vs 5 (Covetous); child memory copy timing (Sandbox cell; implied by Decide-before-Act);
AtomPush's refill cost (stored replay event order).

---------------------------------------------------------------------------------------------------
## 8. Round 5: VEX/AVX-128 (2026-11-08)
> **Broken on the site (calib-s), do not submit: Woe, Conceit, Endemic.** Probe calib-s (Sandbox 104136) shows the
> site's QEMU has Unicorn's VEX bug: `vpcmpeqb xmm2, xmm0, xmm1` computes xmm2 = (xmm2 == xmm1), the first source is
> ignored. Woe died in Sandbox 104123 and 104128 (peak 4-5 cells while Scourge grew). `cells/vex_emu.py` now emulates
> the site's behaviour and `cells/check_cells.py` rejects any VEX op whose destination differs from its first source;
> all three variants fail it (Unicorn diff 86,051 / 80,808 / 565,111 mismatches; the parents still pass with 0). The
> rest of this section is the record of the round as built and is kept unchanged; its counts and sim numbers assume
> the documented three-operand form, which the site does not run.

Rounds 1-4 and every cell above stay as they are; round 5 adds three VEX variants. Each one makes exactly its
parent's decisions and differs only in instruction counts, so each ladder comparison measures speed alone.

### 8.1 Instructions on the site (calibration cells in `cells/calib/`, data/site-observations-2026-11-08.md)
| Works | Faults (invalid_insn every call) |
|---|---|
| SSE2 (movdqu, pcmpeqb, pmovmskb, por, pxor) | popcnt (f), SSSE3 pshufb (g), SSE4.1 ptest (h), SSE4.2 crc32 (m) |
| AVX-128 VEX forms of SSE2 ops: vpcmpeqb reg-reg (k) and with an UNALIGNED memory operand (p); vpxor, vpmovmskb (q) | BMI1 andn (i), BMI2 pext (j), AVX2 ymm (l) |
| | VEX forms of SSSE3/SSE4.1 ops: vpshufb (n), vptest (o) |

Verified at entry, on every call: rax = 0 (c); **xmm0..xmm15 all zero** (probe q, `cells/calib/q_xmm_zero.asm`,
22 insns, 0 faults); **rbx, rcx, rbp, r8..r15 zero** (probe r, `cells/calib/r_gpr_zero.asm`, 15 insns, 0 faults).
Only al is read as the action. Legacy-SSE memory operands must be 16-byte aligned; VEX memory operands need not be.

**What VEX buys.** A VEX compare is non-destructive with a separate destination (`vpcmpeqb xmm0, xmm3, [mem]`),
so one raw view window loaded once can be compared against several constants, one instruction each. It does not
make the first compare cheaper: one operand has to be in a register, so load + compare is still 2 (`movdqu` +
`vpcmpeqb`), and the F5 bite stays at 5. The zero registers do not help these cells: comparing against zero finds
EMPTY squares, but the bite needs ENEMY (2), and an empty-square compare is already one VEX instruction against a
memory constant. They could save an instruction in a design that needs a zero or an empty mask before any load.

**Tooling.** Unicorn 2.1.4 ignores VEX.vvvv (it runs `vpcmpeqb xmm0, xmm3, [k]` as xmm0 = (xmm0 == k)), so
`cells/check_cells.py` decodes and executes vpcmpeqb itself (`cells/vex_emu.py`, self-tested at start; any other VEX
op is refused). Unicorn also runs popcnt/SSSE3/SSE4/BMI that the site rejects, so every cell is checked against a
site-verified instruction list (`ALLOWED`); VEX cells may have no legacy-SSE memory operand, so they need no
`align 16`.

### 8.2 The three variants (names from docs/cell_names.txt)
| Cell (files) | VEX variant of | Change | Saved |
|---|---|---|---|
| **Woe** (`cells/gen_woe.py` -> `woe.asm`) | Scourge (the scourge brings woe) | The bite loads view idx 6..21 once into xmm3 (bite mask shifted one lane, table 2211 bytes); gate 1 is `vpcmpeqb xmm1, xmm3, [kRefill]` instead of movdqu + pcmpeqb | -1 on every path after the bite |
| **Conceit** (`gen_conceit.py` -> `conceit.asm`) | Covetous (greed grown vain about its speed) | The bite keeps its raw window 7..22 in xmm3; the split check is `vpcmpeqb xmm0, xmm3, [kEmpty]` instead of a reload + compare | -1 on every path through the split check |
| **Endemic** (`gen_endemic.py` -> `endemic.asm`) | Contagion (a contagion that settles in) | Woe's bite and gate 1; the boxed block makes its empty masks with `vpcmpeqb xmmN, xmmView, [kZero]` instead of pxor + pcmpeqb | -1 after the bite; -3 on the boxed block from the grab gate on |

Each cell's header comment names its parent. All three use only movdqu, vpcmpeqb, pmovmskb, por and integer ops,
and none relies on the zero registers (constants are in memory; same counts either way).

### 8.3 Instruction counts per path (every executed instruction incl. taken jumps and ret)
| Path | Scourge | **Woe** | Covetous | **Conceit** | Contagion | **Endemic** |
|---|---|---|---|---|---|---|
| bite (adjacent enemy) | 5 | 5 | 5 | 5 | 5 | 5 |
| refill (freed front square, e >= 12) | 11 | **10** | - | - | 11 | **10** |
| split, e >= 16 (Covetous: no enemy in view / enemy in view) | 11 | **10** | 22 / 24 | **21 / 23** | 11 | **10** |
| split, 5 <= e < 16, no enemy in the 5x5 | 24 | **23** | 22 | **21** | 26 | **25** |
| split, 5 <= e < 16, enemy in view, tick >= 2980 | 25 | **24** | 26 | **25** | 25 | **24** |
| hold (rest), enemy in view, tick < 2980 (Covetous: e < 47) | 27 | **26** | 23 | 23 | 28 | **27** |
| rest, e < 5 | 17 | **16** | 9 | 9 | 17 | **16** |
| rest, boxed, below the feed / grab floor | 17 | **16** | 24 | **23** | 17 | **16** |
| scout move | - | - | - | - | 40 | **39** |
| boxed e 20, friends 20/5/9/5 (feed; Covetous rests) and the longest feed path | 48, max 53 | **47, max 52** | 24, max 60 | **23, max 59** | 82 | **79** (parent - 3) |

### 8.4 Squares 2 and 22 (beyond UP / DOWN) in the refill window: not free
No 16-byte window holds view idx 2..22 (21 bytes). Reading them takes a second window compare plus a merge into
the table index (pmovmskb, shift, or): at least 3 more instructions on the 10-instruction refill path, which is
the one path that must stay fast. A check only on the hold path (5 <= e < 16, enemy in view) would cost nothing
elsewhere but would refill there at ~30 instructions and change decisions: a separate bet, not built.

### 8.5 Equivalence checks
- `cells/check_cells.py` (NASM + Unicorn with VEX emulation): ALL CHECKS PASSED. Woe vs `sim/cells_ref.woe`
  100,256 cases, Conceit 98,304, Endemic 610,200 (memory states, positions, memory compared after the call), all
  0 mismatches in action and instruction count. The same grids as their parents (which still pass with 0).
- `sim/cells_ref.woe/conceit/endemic` = the parent's policy with the saved instructions subtracted;
  `sim/tests/test_vex.py` checks the same action and parent minus the saving on every view of a 15,000+ grid,
  the tables (Woe's bite table = Covetous's shifted one lane; act/thr = Scourge's), the paste rules and the
  instruction list. 261 tests pass.

### 8.6 Sim results (indicative: the fight/refill model is weak, 47/62 calibration checks on the then 36-match pool; current state: 10.6)
`python sim/batch.py --set vex` (120 games, seeds 1-8 per mix, 4 workers, 2613 s; `sim/out/vex-20261108-092732.md`).
Points per game (win %) over 8 games:

| Mix | Variant | Parent | Others |
|---|---|---|---|
| Woe, Scourge, rpump, ratompush (head to head) | **Woe 2.38 (62%)**, pop 1915 | Scourge 1.75 (12%), pop 1056 | ratompush 1.62 (25%), rpump 0.25 |
| Conceit, Covetous, rpump, ratompush | **Conceit 1.88 (0%)**, pop 485 | Covetous 1.00 (0%), pop 128 | ratompush 2.62 (88%), rpump 0.50 (12%) |
| Endemic, Contagion, rpump, ratompush | **Endemic 2.75 (75%)**, pop 2098 | Contagion 1.75 (12%), pop 1299 | ratompush 1.38 (12%), rpump 0.12 |
| X + rpump, ratompush, rblind3 | Woe 2.00 / Conceit 1.50 / Endemic 2.00 (0%) | Scourge 2.00 / Covetous 1.50 / Contagion 2.00 (0%) | rblind3 3.00 (100%) every time |
| X + rbrawler, ratompush, walker | Woe 2.50 (62%) / Conceit 1.62 (0%) / Endemic 2.75 (75%) | Scourge 2.50 (62%) / Covetous 1.62 (0%) / Contagion 2.75 (75%) | rbrawler 2.00-2.62 |

Reading: against the rival models the variants play the **same games** as their parents (Woe, Endemic: identical
numbers; Conceit within a few cells): no rival path in the sim lands on 10-11 (or 21-26), so one instruction
changes no turn order. Head to head a variant wins every contested refill against its own parent (10 before 11),
which is what decides those mixes. So the saving is worth something only where a rival's path count equals the
parent's (a tie, broken at random) or falls between the two; the real ladder's refill counts are not known that
precisely. The gain is free: same decisions, no path slower.

### 8.7 Recommendation
(Follow-ups superseded by 10.4.)
(Superseded by calib-s, see the note at the top of section 8: none of the three may be submitted.)
Submit **Woe** first: it is Scourge (1st on the leaderboard) with every refill and split one instruction earlier
and nothing slower, so it can only win ties Scourge would lose; head to head it beats Scourge 2.38 to 1.75 points.
Then **Endemic** for Contagion (same reasoning; also -3 on its grab/feed paths). Conceit last (Covetous's
split paths at 21-25 are rarely contested). Before any ladder use: one Sandbox game each (scripted POST, not the
form) to confirm 0 faults and the counts on the site (bite 5, refill 10); the ladder swap needs the user's approval.

Open: probe q (xmm zero at entry) and probe r (GPRs zero) are done (verified above); Woe, Conceit and Endemic have
not run on the site yet (a Sandbox game before any ladder use; no ladder change without the user's approval).

## 9. Round 6: Complacency = Scourge plus early free splitting (2026-11-08)
### 9.1 The bet
Pull 3 (data/scourge-losses-2026-11-08.md): Scourge loses the land grab, not the late fights. Winners lead from about
t21; at t200 Scourge has ~800 cells vs ~2400 for AtomPush/AtomCrasher; it reaches pop 128 / 512 at t36-44 / t81-175
vs t28-33 / t56-82 for the winners. Suspected cause (10.2 later placed the deficit in the first ~35 ticks and in split geometry): the prey hold (5 <= e < 16 with an enemy anywhere in the 5x5:
rest until t2980). Contagion's games (data/contagion-games-2026-11-08.md) point the same way: it wins the pre-contact
race and loses t75-t200, right after first contact, still with the prey hold. **Complacency** (unconcerned by
enemies in view; `cells/gen_complacency.py` -> `cells/complacency.asm`) is Scourge with exactly one change: no prey
hold while tick < T. Built on Scourge, legacy SSE2 only: it was drafted on Woe, but calib-s showed Woe's VEX form is
broken on the site (section 8 note).

### 9.2 T chosen: never hold (T = 3000)
Sweep `python sim/batch.py --set complacency-t` (136 games, seeds 1-8, 4 workers, below-normal priority, 3148 s;
`sim/out/complacency-t-20261108-104611.md`), T in {200, 300, 500, never} plus the "hold only for a diagonal enemy"
probe (diag: view 6/8/16/18, which gate 1's mask already holds, so `test ecx, DIAG` would cost 2-3):

| Mix | T=200 | T=300 | T=500 | never | diag | Scourge alone |
|---|---|---|---|---|---|---|
| X, scourge, rpump, ratompush: X pts (win %), final pop | 2.38 (62%), 1871 | 2.38 (62%), 1870 | 2.38 (62%), 1870 | **2.50 (62%), 1907** | 2.38 (62%), 1826 | Scourge 1.75 (12%), ~1125 |
| X, rpump, ratompush, rblind3 | 2.00 (0%), 1066 | 2.00, 1066 | 2.00, 1077 | **2.00, 1204** | 2.00, 1026 | 2.00 (0%), 993 |
| X, rbrawler, ratompush, walker | 2.50 (62%), 1944 | 2.50, 1940 | 2.50, 1942 | **2.50, 1974** | 2.50, 1878 | 2.50 (62%), 1705 |

Win rates are the same for every T (and in the rival fields the same as Scourge's): the sim says the change wins
land, not games. Final population is highest with "never" in all three mixes, and "never" is also the simplest code
(the 5x5 check is gone) and the fastest middle path (16). The diagonal hold is worse than any T (fewer cells, same
wins), so it was not built. T >= 200 also matches the Contagion data (the no-hold window must cover t75-t200).

### 9.3 Instruction counts per path (every executed instruction incl. taken jumps and ret)
| Path | Scourge | **Complacency** |
|---|---|---|
| bite (adjacent enemy) | 5 | 5 |
| refill (freed front square, e >= 12) / split e >= 16 | 11 | 11 |
| split, 5 <= e < 16, no enemy in the 5x5 | 24 | **16** |
| split, 5 <= e < 16, enemy in the 5x5, tick >= 2980 | 25 | **16** |
| same, tick < 2980 | rest (hold), 27 | **split, 16** |
| rest, e < 5 / boxed below the feed floor | 17 / 17 | 17 / 17 |
| feed block (boxed, e >= 16) | 21 + ..., max 53 | same |

(A finite T would cost: early split 17, and after T Scourge's 5x5 paths + 2: 26 / 27 / hold 29.)
The bite, gate 1 and the tables are Scourge's byte for byte (tested); kTwoLo/kTwoHi are gone.

### 9.4 Checks
- `cells/check_cells.py` (NASM + Unicorn, WSL): Complacency vs `sim/cells_ref.complacency` 200,512 cases (Scourge's
  grid, ticks 0/1/2979/2980), 0 mismatches in action and count; and its action vs `cells_ref.scourge` on every case:
  equal except the 7,566 prey-hold states (Scourge rests on its 27 path, tick < 2980), where it splits into the
  first freed, else first empty, neighbour of DOWN, RIGHT, UP, LEFT: 0 mismatches. All other non-VEX cells still
  pass; the run's 33 problems are all Woe/Conceit/Endemic (broken by design since calib-s).
- `sim/tests/test_complacency.py` (9 tests: ref vs a spec-written expectation for T 200/300/3000, generator = committed
  asm, bite/gate-1 and tables = Scourge's, no VEX, paste rules, a real-engine match). 274 tests pass.

### 9.5 Sim results (indicative: early growth is the better-modelled part, late fights are weak)
Early growth, mean pop at t50 / t100 / t200 and median first tick to pop 128 / 512 (sweep, 8 games per mix):

| Mix | Complacency | Scourge |
|---|---|---|
| head to head (+ rpump, ratompush) | 222 / 673 / 1229; 37 / 83 | 193 / 540 / 846; 40 / 94 |
| + rpump, ratompush, rblind3 (Scourge in its own mix) | 216 / 641 / 1065; 37 / 87 | 218 / 621 / 1023; 37 / 89 |
| + rbrawler, ratompush, walker | 223 / 695 / 1350; 37 / 89 | 221 / 665 / 1221; 37 / 91 |
| real ladder (pull 3) | - | Scourge ~500 at t100, ~800 at t200; 36-44 / 81-175; winners 28-33 / 56-82, ~2400 at t200 |

Reading: the gain shows from t100 on (+3% to +11% at t200 against the rival models, +45% head to head, where
Scourge's hold is triggered by Complacency itself) and lasts (final pop +7% to +21%). But the sim's rivals do not
grow like the real Atoms (ratompush reaches 512 at t75-84, real AtomPush t56-82, and only rblind3 at t64 comes near),
and the sim's Scourge already reaches 128 / 512 at t37 / t89-94, the fast end of the real range: the sim does not
reproduce Scourge's real land-grab deficit, so it cannot say how much of that deficit the hold causes. Real test:
one Sandbox game, then the ladder (user approval).

### 9.6 Follow-ups
(Superseded by 10.4.)
- The same change on **Contagion** (which already has the faster opening and loses t75-t200 after first contact,
  data/contagion-games-2026-11-08.md) as a separate cell; not built here (one bet per cell).
- Before any ladder use: one Sandbox game (scripted POST, not the form) for 0 faults and the counts (bite 5,
  refill 11, middle split 16); the ladder swap needs the user's approval.

### 9.7 Confirmation on new seeds, and the head-to-head numbers are start luck
- `python sim/batch.py --set complacency` (seeds 9-16, 40 games, 3 workers, 1137 s; `sim/out/complacency-20261108-112036.md`):
  vs rpump/ratompush/rblind3 Complacency 2.00 pts (0% wins), final pop 1080 vs Scourge 2.00 (0%), 832; pop t200 722 vs
  650, time to 512 t113 vs t132. Vs rbrawler/ratompush/walker 2.12 (38%) both, final pop 1772 vs 1678, t200 1042 vs 944.
  Head to head (+ rpump, ratompush) the result flipped: **Scourge 2.50 (75%), Complacency 1.75 (12%)**.
- `python sim/batch.py --set complacency-mirror` (the two swapped in the mix, seeds 1-16, 16 games, 516 s;
  `sim/out/complacency-mirror-20261108-112938.md`): Complacency 2.25 (50%), final pop 1882; Scourge 2.19 (38%), 1445.
  Paired by seed over both orders (32 games): Complacency finished ahead of Scourge in 8 of 16 per order and **on no
  seed in both orders**, i.e. in the sim the head-to-head winner is fixed by the start slot, not by the cell. So the
  "62% head to head" in 9.2 (and Woe's 2.38 vs 1.75 in 8.6, the same seeds and the same numbers) measure start luck,
  not the change. What survives: same win rates, more land (final pop +6% to +30%, t200 pop +4% to +11% vs the rival
  models), and no sign that dropping the hold costs anything in the sim.
- Verdict (indicative): a free, low-risk change in the sim; whether it fixes the real t21-t200 deficit can only be
  seen on the site (Sandbox, then the ladder with the user's approval).

---------------------------------------------------------------------------------------------------
## 10. Round 7: full review after pull 5 (2026-11-08)
Sources: pulls 1-5 (148 replays; 135 in the validation pool), `data/pull5-games-2026-11-08.md`, `data/site-checks.md`,
the docs re-review (note before section 1), and sections 1-9. Planning only: no cell is built and no ladder change
is made without the user's approval.

### 10.1 Where things stand
- Ladder at pull 5: **Complacency 1576 (1st, 282 games)**, Contagion 1550 (2nd, 460 games), AtomPush 1483, AtomCrasher
  1432. In the 480-game list (about 80 minutes) Complacency won 81% and Contagion 77%, against AtomPush 73% and
  AtomCrasher 64%. No rival changed version since the simulator was tuned.
- Our two cells have the best late game on the board. Median final population in pull 5: Contagion 2590 and
  Complacency 2302, against AtomPush 2168 and AtomCrasher 1942. The pumps (Aegis, Noob+, Noob++, Bouncer) are at
  or near 0 by t1000-t2000.
- Our losses are almost all 2nd places with a frozen front. In 14 of the 15 pull 5 losses the winner was
  ahead at t200, by 1.5x or more in 10 of them (for example 106249: 620 against 2496), and in most of them the land
  then changed little.
  Late fights hardly ever cost us a game. The grab does.

### 10.2 The grab deficit is in the first ~35 ticks, and it is about geometry, not energy
Median over pull 5 (all games of each cell):

| Cell | t25 | t50 | t100 | t200 | first tick at 128 / 512 | win % (sample) |
|---|---|---|---|---|---|---|
| Complacency | 69 | 239 | 664 | 1213 | 36 / 84 | 61 |
| Contagion | 71 | 274 | 751 | 1344 | 34 / 72 | 56 |
| AtomPush | 96 | 348 | 994 | 1579 | 29 / 63 | 59 |
| AtomCrasher | 78 | 295 | 899 | 1565 | 32 / 68 | 60 |
| Noob++ (pump) | 100 | 331 | 799 | 1266 | 29 / 70 | 5 |
| Aegis (pump) | 85 | 357 | 961 | 1322 | 30 / 63 | 19 |

(The sample over-samples our losses; the win % column is for this sample only.)

What the replay mining rules out (pulls 3-5, cells that rest or fail with no event, t < 500):
- **Not failed actions.** Our cells' share of zero-gain ticks below the cap is 0.6-0.8%, lower than every rival
  (Atoms 1.2-1.3%, pumps 1.5-4.5%).
- **Not fat interiors.** Untouched AtomPush and AtomCrasher cells sit at the cap 87-89% of the time (mean energy
  48), more than ours (36-43% at the cap, mean 42-43), and they still grow fastest. Pumps keep interiors at 2-6
  energy and grow about as fast as the Atoms, but then lose everything.
- **Not child size.** The mean child energy at birth is 4.0-4.7 for every strong cell, ours included.

What is left: the first 30 ticks, when almost every cell is on the edge and the shape of the colony decides how many
cells can split next tick. Our cells split into the first empty neighbour in the order DOWN, RIGHT, UP, LEFT. This
packs children against each other, so fewer of them have an empty neighbour when they reach 5. The Atoms "split
spread out" (section 1.2). Before t35 no rival model is involved: the simulator models own-colony growth exactly
(its Scourge and Complacency reach 128 at t37, real t36-44), so this question can be settled offline.

### 10.3 What the new rule facts change
- **Move-freed squares open the same tick** (Rules p.2), death-freed squares the next tick. A front cell that moves
  forward can be replaced by a split from behind in the same tick. This makes Pestilence (7.1) cheaper than thought.
- **Feed reaches enemies.** It gives energy away, so it is no attack; a feed into an enemy is a wasted action, and
  the feed code must keep checking the target's owner (it does today).
- **Cell memory and the stack are allowed.** "No memory on the hot path" stays a speed rule. Memory makes Conviction
  (7.2) and a stored origin (Contagion) safe to rely on. Stun survival is implied by Decide-before-Act.
- **Matches are deterministic from the seed.** A Sandbox game with the same seed and the same opponents is an exact
  A/B: swap only our cell, and every difference comes from the change. Use it for mechanical changes; the ladder
  (>= 300 games) is still the judge of strength.
- **Total instructions break ties** after population and energy. Exact ties only: no design change.
- **SSE3** adds nothing the cells need.

### 10.4 Updated plan (replaces the follow-ups in 8.7 and 9.6)
Section 11 replaces items 1-3 and parks items 4-5.
Ladder: Complacency and Contagion stay. The third slot is free (Scourge retired). Ranked:

1. **Schism** (new; S-M, fits K): Complacency with a growth opening, changing only the split direction. While there
   is no enemy in the 5x5 view, a cell splits into the empty neighbour with the **most empty squares around it**
   (counted in the 5x5 view; ties away from the stored origin, else the fixed order). Bite, refill, feeding and
   endgame as Complacency. Target: first tick at 128 / 512 of 29-30 / 63-65 (AtomPush), against 36 / 84. Cost: a
   table lookup on a mask of the 5x5 empties (`pcmpeqb` + `pmovmskb`, as gate 1 does), about +3 to +5 instructions
   on the grab split path only; bite (5) and refill (11) unchanged. Tests: (a) a solo-colony simulator study of
   split rules (no rivals, so no rival-model error; 50 starts x 200 ticks, minutes of CPU); (b) Unicorn check;
   (c) one Sandbox A/B pair against Complacency on the same seed; (d) the ladder only with the user's approval.
2. **Early outward feeding for Schism** (only if 1 still trails at t50-t100): during the grab, cells with no empty
   square in the 5x5 view feed outward from the stored origin at a low floor (D = 6-8), only to a friend with an
   empty neighbour, and stop at first contact so the interior fattens for the refill race. "Pump first, fort
   later": the pumps show the opening speed; the Atoms and our cells show that fat interiors win from t500 on.
3. **Pestilence** (7.1): refill by MOVE of a fat front cell, backfilled from behind in the same tick (10.3).
4. **Conviction light** (7.2): a queued refill after the F5 miss, only if the refill race shows up again as a cause
   of lost games. Pull 5 shows grab losses, not race losses.
5. **Anxiety, Abasement, Misfortune** (7.3-7.5): unchanged, lower value than 1-2.
Retired: the VEX variants (section 8); Doctrine (feeding depth is item 2 now); Famine and Bane (as in 7).

### 10.5 Fresh-start design (if the project started over today)
1. **Growth curve first.** Write the opening for the shape of the colony, measured against the best real curve
   (AtomPush: 128 at t29, 512 at t63). The grab decides most games we lose, and the simulator models it exactly.
2. **Two-phase kernel, per cell, with no colony-wide state.** Phase 1 (no enemy in the 5x5): spread-out splits,
   optional outward feeding. Phase 2 (enemy in view): F5 bite, fast refill of freed front squares, capped-donor
   feeding, fat interior. Each cell decides from its own view: no colony timer to tune.
3. **Split directions from the view, not a fixed order.** The main thing our cells lack (10.2).
4. **Instruction budget on contested paths only.** Turn order follows that call's count, so only the bite (5) and
   refill (11) race. The per-call average (Complacency 46, Contagion 78, Atoms 35) matters only for the tie-break.
5. **Work order.** Solo-growth simulator, then Unicorn, then a fixed-seed Sandbox A/B (10.3), then the ladder (user
   approval). The rival-model simulator only for questions after contact, with its validation state in view (10.6).
Unchanged: the F5 bite, the refill race, capped-donor feeding and no prey hold (all confirmed by pull 5).

### 10.6 Simulator state (measured 2026-11-08 on the 135-match pool; no tuning, no code change)
| Set | n | Sim same winner | Checks | Rating baseline | Win-share baseline |
|---|---|---|---|---|---|
| Old TEST (rerun) | 21 | 81% | 48/62 | 33% | 48% |
| TEST | 45 | 71% | 51/63 | 49% | 53% |
| TEST, pull 5 only (never seen in tuning) | 24 | 62% | 46/59 | 62% | 58% |
| FIT | 90 | 70% | 47/63 | 44% | 59% |
Unit tests 295/295. On fully held-out pull 5 games the simulator picks the winner no more often than "the higher
pre-match rating wins". Main causes: the Atom models feed 4-5x too much (36-38 feeds per eat against 7-9 real) and
grow 25-30% too slowly to t100; the pump models feed about half the real amount and hold about 6 more energy at t200;
Noob+ keeps its land late in the sim (real median end 0, sim 1821; 8 wrong winners); Scourge over-wins in games the
real winner fills by t300; rooby dies too often. Next tuning targets when the pause ends: (1) the Atom economy,
(2) Noob+'s late land loss (add a rival t500/end check), (3) pump feeding. Ceiling not rerun (about 65-90 min; needs
a workers option and its seed-0 input file, which a fresh checkout lacks).
Consequence for design work: trust the simulator for own-colony growth before contact (10.2, the Schism study), not
for win rates against the rival field until the Atom and Noob+ models are fixed.
Update, same day: `replay_check.py` found no engine rule error. The Atom and Noob+ models changed, but Atom feeding is still wrong. Current state: `architecture/simulator.md`.

## 11. Final cell plan (2026-11-08)
This plan replaces further design rounds. A climber aims to raise the rating. Policy names such as a+f6x are defined in `sim/growth.py`. Labels: [M] measured, [R] reasoned, [E] estimate. Contact results in the simulator are not evidence.

### 11.1 Schism (climber; built first)
- Base: `cells/gen_complacency.py`. Split order does not change. No memory.
- New rule: no enemy in the 5x5, no empty neighbour, energy >= 6: feed the first friend (UP, RIGHT, DOWN, LEFT) that has an empty neighbour. This is policy a+f6x in `sim/growth.py`.
- Paths: bite 5, refill 11, split 16 do not change [M]. New feed 32 to 48 [M]. The old feed block at energy >= 16 exceeds the 53-instruction design limit, because the new checks run before it: longest 63 with an enemy in the 5x5, 86 with no candidate [M]. Rest at energy 6 to 15: 27 or up to 50 [M]; Complacency 17. The site cap is 1000.
- Benefit in solo growth: 128/512 cells at t31/t63, 1110 cells at t100; Complacency 37/79.5, 751 [M]. AtomPush real: 29/63.
- Why this rule: with feeding on, the view split adds no tick (w+f6x 31/62.5). Memory adds nothing (a+f6 31/62). This corrects 10.2: feeding gives most of the gain, not geometry.
- Risk: thin cells behind the front at contact. Deep cells have no target, so they stay fat [R].
- Status: on the ladder as cell 176 since 2026-11-08 (the owner's action).

### 11.2 Pestilence (unique mechanic; second)
- Base: the higher rated of Schism and Complacency.
- Change 1: refill path, energy >= 20: MOVE into the freed square, not split. The bite runs first, so the vacated square has no enemy neighbour [R].
- Change 2: same-tick backfill. An idle cell behind a friend with energy >= 20, with an empty square beyond that friend and an enemy beside that square, splits into the friend's square. This is a prediction, because Decide comes before Act. The backfill path must be longer than the move path. A miss costs one rest.
- Paths: refill limit 14 [E]. Above 14, drop the change.
- Benefit: 0% of 375k mined refills are moves [M]. Carries 20-50 energy forward; a child has 6 [R]. Ladder gain unknown.
- Risk: slower refill loses races.
- Slot: the slot Complacency left on 2026-11-08.
- Built 2026-11-09 (`cells/gen_pestilence.py`): Schism base, change 1 only (change 2 is a turn-order guess; add it only if the Sandbox shows moves working). `cmp sil, [mv_tbl + rcx]` / `jae move` before gate 1 loads its action: the move refill takes 13; every other path after the bite costs 2 more than Schism's (split 13). A check after gate 1 would cost 15, because gate 1 leaves through the return address. Binary 24,410 bytes. `check_cells`: 100,256 Unicorn cases and 524,288 boxed cases, 0 mismatches.

### 11.3 Famine (climber; third)
Section 7 used this name for a harvesting idea that was never built. This is a new design.
- Base: Contagion generator. Grab assist: floor 8 to 6; remove the target limit (e <= 4).
- Paths: contested paths do not change [R].
- Benefit: w+f6x against w+f6x4: t100 1081/1000, 512 at 62.5/64.5 [M, Complacency base]. Contagion real: 34/72.
- Risk: no solo data on this base. Section 6 rejected deep feeding (D ~ 6) for a losing economy in pull 2; the evidence here is solo growth only.
- Slot: replaces Contagion after the gate.

### 11.4 Gate
Schism at >= 300 games, rating >= Complacency's final 1516. Fail: remove Schism; Pestilence on the Complacency base takes its slot; no Famine.
Result 2026-11-09: passed. Schism 1653 after 1321 games (1035 wins), 1st on the leaderboard; Contagion 1631, 2nd.

### 11.5 Steps
Claude: build, tests, `check_cells`, Unicorn counts. Owner (results in `data/site-observations-2026-11-08.md`):
1. Done for Schism. The Sandbox has no seed control, and 128 cells is out of reach with 4 colonies on 16x16. Three games each against Scourge, Covetous, Contagion: Schism places 2, 1, 2; Complacency 2, 2, 3; 0 faults.
2. Sandbox, Pestilence, one game. Record move refills, same-tick backfills, faults. Backfill hits under 50%: remove change 2.
   Done 2026-11-09 (cell 180, change 1 only): Sandbox 116745 vs Scourge/Covetous/Contagion: 2nd, pop 71 (Contagion 76), 0 faults, insns avg 53 max 88. Move refills not counted (needs the replay).
3. Create the cell by scripted POST (the form ladders it at once). The owner ladders it. Ratings arrive in `data/site-checks.md`.

### 11.6 Supersedes
10.4 items 1-3, the 7.1 test. Parked: 7.2-7.7, 10.4 items 4-5.

### 11.7 Top risks
| Risk | Early sign |
|---|---|
| Thin band loses contact (feed level 6 repeats the section 6 concern) | Sandbox lead at t50 gone by t200 |
| Site differs from the simulator (as with Woe) | Sandbox fault, or peak under 10 cells |
| Pestilence weakens the refill | Rating under 1450 at 100 games |
