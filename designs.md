# CellHack2 cell designs — round 4 (2026-11-08)

Planning only. Round 4 rests on both ladder data pulls (`data/ladder-data-2-2026-11-08.md` is the main source,
991 matches and 36 decoded replays), the site calibrations (`data/site-observations-2026-11-08.md`), the reviewer's
round 3 review (`reviews/r3-review.md`) and the lead's decisions on its G1-G20 (end of `reviews/decisions-r1.md`).
History: `reviews/designs-r1..r3-snapshot.md`.

**Names** (user's choice): cells are named from `docs/cell_names.txt` (Stellaris names), matched to behaviour.
Avarice = our ladder cell Sprint (eats greedily, never feeds; ladder name and `cells/sprint.asm` stay Sprint).
Covetous = Avarice's quick successor (on the ladder since 2026-11-08). Scourge, Contagion = the next two cells.
Doctrine = a later feeding-depth variant. Dogma (formerly Hold) is retired. The sim may use old names in code.

**What changed since round 3, and why**
1. Pull 2 overturned "land is decided by t300-500": only 2 of 36 replays are frozen by t500; median freeze 2076.
   Late conversion of land matters as much as the grab.
2. A flat 5-instruction bite with no memory exists (Covetous, verified on the site): `or al,[bite_tbl+rcx]` with
   rax = 0 at entry, then `jnz EXIT_ADDR`. This supersedes every lock form for the bite (G3 asked for the post
   lock; its 5 is now free without memory, its first contact 11 was worse).
3. Sprint loses to HammerSpb on the refill race, not bite order (G2): it kills thousands of AtomPush cells and
   gains no land, because AtomPush refills freed squares faster (split path <= 20, children 5-7). A fast refill of
   freed front squares is the kernel's main new feature.
4. Deep pumps (interior ~6-10) are the field's losing economy (G1): Dogma is dropped. Feeding comes from capped
   cells only, plus a moderate donor floor D (12-16).
5. The "+3 on feed" and "+1 idle" are feed 2 + rest 1 and rest, which replays do not log (G4). Income = cells
   below the cap that rest. Energy above ~50 is wasted.

---------------------------------------------------------------------------------------------------
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
2. Does memory persist when a cell is stunned? Matters only if a design uses memory on the front.
3. Resolved by replay mining: an event-free cell below 50 gains +1 in 95-99% of ticks, at 50 never. Income = resting cells below the cap.
4. Exact cap (50 at Tidy, mid-tick 52-56 seen).

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
  instruction count. Sprint (split path 19-21) won 0.5% of contested squares vs AtomPush and 3.6% vs AtomCrasher;
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
  feeding code (G12): Sprint's late gains came from re-occupying dead colonies' squares fast.
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

**Covetous** is the interim data collector: F5 + capped feeding, otherwise Sprint. Its ladder record against
Sprint's measures what the bite alone is worth, and it probes the rivals' "6" directions (1.3.1).

**Scourge** is the next cell: Covetous plus the refill and D = 16. It targets HammerSpb directly (the refill race).

**Contagion** adds the grab tools to Scourge's kernel.

**Ladder slots (3):** Sprint and Covetous now. Scourge takes the third slot. When Contagion is ready, it replaces the
weakest of the four by then, and only after each has >= 50 games (G11). Every ladder change needs the user's approval.

---------------------------------------------------------------------------------------------------
## 4. Experiments (simulator; max 4 of 6 cores, below-normal priority, run as background batches)
The simulator's rival models are being refitted to pull 2's fingerprints (pump rivals were too fat, the late
game too slow; `issues.md`). Trust E1-E4 only after that validation rerun.
| # | Question | Setup | Changes |
|---|---|---|---|
| E1 | Refill race (G13) | refill R in {3, 6, 8} vs no refill, against the fat AtomPush-like rival | Scourge's R; squares gained per 100 ticks after first kill |
| E2 | Feeding depth (G14) | D in {8, 12, 16, 20} with capped donors, vs fat, pump and flat-6 rivals | D for Scourge, Contagion, Doctrine |
| E3 | Grab (G15) | G in {8, 12}, S in {0, 2}, measured start distribution; targets 300-400 / 700-1400 / 1300-2300 at t50/100/200 | Contagion |
| E4 | Counter-moves (G16) | a blind-3 rival; a rival with a 4-instruction refill in its fast direction | whether we need a faster answer |
Deferred: harvesting (G17: a second-row cell eating its own capped front cell); only as an experiment.

---------------------------------------------------------------------------------------------------
## 5. Data plan
- Covetous's first ~50 games: win rate and head-to-heads vs Sprint's (scheduled check), and its bite-first share in
  each rival's "6" direction (1.3.1), from one or two chosen replays only.
- Offline mining of the 35 stored replays: done (data/replay-mining-2026-11-08.md, tools/pull2/mine.py, a pure-Python decoder).
- Watch the leaderboard (small page) for rival version changes before fetching anything large. Fetch gently.

---------------------------------------------------------------------------------------------------
## 6. Rejected or retired
- Dogma and deep feeding (D ~ 6): losing economy in pull 2 (G1).
- Checked lock and pre-arming: refill at ~20 loses the race (G3).
- Post lock as the bite: F5 gives the same 5 without memory; kept only as the refill fallback (2.2).
- Scouts S = 4 and corner logic: starts are random and contact comes early (G9).
- Sprint's F6 as the base: F5 replaces it in every new cell.
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
   whole colony goes to survival mode. Test: replay stat on Sprint's 17 replays.
6. **Famine** (S): harvesting (G17); low value for a fat-interior kernel, better in a pump variant.
7. **Bane** (M): notch traps that bait AtomPush's fixed refill; weak (energy-only, AtomPush banks ~158k).
Dropped: kill-order tricks, staircase fronts, a stateless 4-bite, a 2-instruction blind lock, hidden channels,
parity signalling. Inferred from the Rules (not measured): memory writes happen in Decide, before actions, so
they survive a stun; the cap is applied at Tidy.
Open: rivals' LEFT 6 vs 5 (Covetous); cap timing (replay stat); child memory copy timing (Sandbox cell);
AtomPush's refill cost (stored replay event order).
