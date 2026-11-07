# Round 2 review (Claude) — decisions-r1.md and the round 2 plan (2026-11-07)

Sources read in full: the three doc PDFs, cellhack.inc, the five bot sources, designs.md (round 2),
designs-r1-snapshot.md, r1-rules.md, r1-strategy.md, r1-asm.md, decisions-r1.md, sim/README.md,
sim/engine.py, sim/bots.py. Counting convention: every executed instruction, taken jumps and `ret`
included, unless a section says otherwise. New numbers below come from two short runs of the stage-1
simulator (script kept outside the repo; the setups are described where used so they can be
repeated).

## 0. Verdict in ten lines

1. The arithmetic in decisions-r1.md is right: Hunter 7/10/13/16/17/20, the D,L,U,R static order
   4/6/8/10 beats Hunter in every direction, F6 is 6 flat with a 4-instruction miss, the checked lock
   is 5 locked and +3 elsewhere.
2. The lock is wrongly placed. It is not a "bet" for one slot: it weakly dominates F6 in every duel
   (5 < 6 wins outright, nothing in the field ties it except another 5) and costs +3 only on paths
   that never contest initiative. It belongs in the kernel. A variant of it also gives a
   5-instruction refill, which is the second initiative number nobody has priced.
3. The multi-enemy handler as planned (kill-first, 14-20 instructions) hands the duel to any 6-13
   rival exactly where fronts break (salients, breaches, triple points). It must stay at 6.
4. "Feeding only delays" is literally true but misleading. In the simulator a feeding defender at 6
   held a 20-wide front against a 5 attacker for 400 ticks with zero loss and lasted ~1000 ticks;
   the same defender without feeding lost 55% of its cells in 100 ticks. Against a competent human
   field, a front with a tied count or a feeding defender is frozen or near-frozen for most of the game.
   So land at freeze time (the first ~200 ticks) decides placement far more often than attrition.
5. Scouts are therefore the biggest strategic lever, not a B-only experiment. MOVE is 1 square/tick
   against a measured 0.23 squares/tick for the splitting front.
6. The lock's advantage depends on the counting convention: if taken jumps are not counted, F6 is 5
   and the lock is 5, a tie. Calibrate that first; it changes design C's reason to exist.
7. A/B/C as the trio is wrong in composition: A is a strictly weaker control (wasted slot), C is a
   one-feature delta. Proposed trio: Hold / Spore / Breach, all on the same kernel with the lock.
8. Put a simple cell on the ladder now to read rival instruction averages and the bot mix from match
   pages. Round 3 should be written with that data.
9. Two fault classes can kill a colony outright: unaligned legacy-SSE memory operands, and unfilled
   or zero table entries. Add: the 64 KB source limit (an 1106-entry `dq` table is ~20 KB of source),
   a duplicated `org`, and NASM's handling of `[table + rax*8]` under `default rel`.
10. Experiments: build the rival set first, then the frozen-front, scout, refill-race and
    multi-enemy tests (section 6). Full 4-way mixes come last.

## 1. Arithmetic checks

### 1.1 Bots (hunter.asm traced instruction by instruction)
`lea`(1) `mov`(2) `cmp`(3) `je`(4, taken) `mov`(5) `add`(6) `ret`(7): UP 7. Each further direction adds
`mov cmp je`(3): RIGHT 10, DOWN 13, LEFT 16. Miss after LEFT = 13; `cmp rsi,6`(14) `jb`(15 taken)
`mov`(16) `ret`(17): rest 17. Not taken: `mov cl`(16) `and`(17) `mov al`(18) `add`(19) `ret`(20): split 20.
All six figures in decisions-r1.md are correct. Medic 6/9/13/9, Walker 7/7/9, Random 4/14, Idle 2:
correct.

"The bots use fewer than 20": with every instruction counted, Hunter's split path is exactly 20 and
has no taken jump, so only an uncounted `ret` makes it 19. Both conventions give the same turn order
except where taken jumps differ between cells (see 1.5). Calibration cells: `mov al,1 / ret` (reads 2
or 1) and `jmp x / x: mov al,1 / ret` (reads 3, 2 or 1).

### 1.2 Static order DOWN, LEFT, UP, RIGHT versus Hunter
`cmp byte [rdi+VIEW_CELLS+17],2`(1) `je`(2) `mov al`(3) `ret`(4): DOWN 4. Each miss adds `cmp jne`(2):
LEFT 6, UP 8, RIGHT 10, all-miss 8. Our DOWN is Hunter's UP (4 < 7), our LEFT is its RIGHT (6 < 10),
our UP is its DOWN (8 < 13), our RIGHT is its LEFT (10 < 16). Correct in every direction. Against a flat
6 it wins at DOWN, ties at LEFT, loses at UP and RIGHT. Moot now that F6 is the kernel, but the same
D,L,U,R order is proposed for the multi-enemy tie and that is checked in 1.4.

### 1.3 F6
`movdqu xmm0,[rdi+39]`(1) `pcmpeqb xmm0,[kEnemy]`(2) `pmovmskb eax,xmm0`(3) `jmp [fight_tbl+rax*8]`(4)
`mov al,imm`(5) `ret`(6). Window bytes 39..54 = indices 7..22: lane 0 = 7 UP, lane 4 = 11 LEFT, lane 6
= 13 RIGHT, lane 10 = 17 DOWN, lane 5 = 12 self (0xFF in kEnemy, so what the view reports for self
never matters). Max mask 0x451 = 1105, so 1106 entries x 8 = 8848 bytes. `pmovmskb` into a 32-bit
register zero-extends, so `rax*8` is safe. Miss = 4 and the jump lands on the slow path. All correct.

Two things to add: (a) with `default rel`, NASM cannot make `[fight_tbl+rax*8]` RIP-relative (an index
is present); it emits an absolute disp32, which is fine at org 0x100000, but write `[abs fight_tbl+rax*8]`
and check the listing so a future NASM warning does not turn into a silent change. (b) 1106 `dq` lines
are roughly 20 KB of the 64 KB source limit; a second qword table of that size would not fit next to the
code and byte tables. Emit tables as `dq` runs with `times` for the filler.

### 1.4 The checked lock (design C)
`movsx rcx,byte [rdx]`(1) `cmp byte [rdi+rcx+100],2`(2) `jne .f6`(3, not taken) `mov al,[rcx+eat_tbl+K]`(4)
`ret`(5): 5 locked. [rdx] = VIEW_CELLS+idx-100 is -61/-57/-55/-51 for U/L/R/D; zero memory reads view
byte 100, inside the 128-byte struct and documented zero, so it never matches. Unlocked paths pay
`movsx cmp jne`(taken) = +3; first contact = 3 + F6 6 + one store = 10. All correct.

Semantics are also right: the target square is re-read every call, so a dead target (square empty at
Decide) or a friend that moved in drops to F6 at +3, and a stale lock inherited by a child either hits
an enemy (good) or falls through. The parent keeps paying +3 on its slow path until something clears
[rdx]; clear it on the slow path (one store, only there).

Variant worth preferring ("post lock"): index the type at the target and add a table byte, so the lock
also refills a freed square at 5 and exits on FRIEND, WALL and zero memory without a compare:
```
movzx ecx, byte [rdx]            ; 0 = unlocked, else VIEW_CELLS+idx-12 (27/31/33/37)
movzx eax, byte [rdi+rcx+12]     ; target type 0..3, or VIEW_W (64) when unlocked
add   al,  [post_tbl+rcx+rax*8]  ; table holds (action - type) & 0xFF; 0 means "run the full path"
jz    .full
ret                              ; 5 when locked: EAT+d on ENEMY, SPLIT+d on EMPTY
```
Index sets {27,31,33,37}+8t for t = 0..3 and 512 for the unlocked case are pairwise distinct (513-byte
table). Unlocked cost is +4 (one more than the checked form), first contact 11. What it buys is section
3.4: the refill race.

### 1.5 Convention sensitivity (nobody has priced this)
If taken jumps are not counted: F6 = 5 (the `jmp` disappears), checked lock = 5 (`jne` not taken is
still executed), post lock = 5, blind lock `or/jz/ret` = 2 (jz taken uncounted). So the whole case for
the lock over F6 rests on taken jumps counting. The Reference says "The engine counts every
instruction" and a QEMU/Unicorn code hook counts every executed instruction including jumps, so the
plan's convention is the likely one, but the first sandbox upload must settle it before C is built.
Under either convention the static D,L,U,R order still beats Hunter.

## 2. Judgement of the decisions and the round 2 plan

What is wrong or incomplete, in order of cost:

W1 (X4, S10, design C). The lock was turned into a slot-level bet on the argument "gains only 1 over
F6". One instruction is the entire game: 5 against 6 is 100/0 on every contact pair, every tick, for
2800 ticks. The +3 is paid only on paths that never contest initiative except races into empty squares
(grab collisions, refills), and the post variant turns the most important of those races, the refill,
from ~25 instructions into 5. The lock is kernel, not C. The real open question for C is whether to go
below 5 (blind 3, section 5.1), and that is a different bet.

W2 (kernel slow path 1). "Kill first, else fixed order" for multi-enemy masks costs 14-20 by the asm
review's own estimate, so a cell with two enemies adjacent runs at 14-20 while its neighbours run at 6.
Those cells are the salient tips, breach cells and triple-point cells, where fronts are decided. Any rival
at 7-13 bites them first. Encode the direction choice in the fight table (still 6): two adjacent enemies
use a fixed order (consistent matching, see 3.3), three enemies bite the direction opposite the one
non-enemy side (the one no friend can reach), four bite anything. Drop kill-first from v1; it only pays
when a <=2 cell is adjacent but is not the matched target.

W3 (1.1.4, S review). "Feeding only delays" undersells it by an order of magnitude; the delay is of
the order of the match (section 3.2). Consequence: the kernel's feeding rules are a first-order
defence against faster rivals, not "tertiary logistics", and the brigade needs producers kept below
the cap (capped resters earn nothing, which is why my naive defender bled 4 energy/tick while holding).

W4 (S4 "accept for B"). Scouts cost ~20 slow-path instructions and 2-4 cells with 5-8 energy at tick
10-25, when nothing is in danger; they multiply early frontier length and claim the centre and dead
quadrants. Given W3, the grab decides placement in most strong matchups. Scouts should be a kernel
feature with the count and bearings as the tuned parameter, and the simulator question is "how many,
where", not "whether".

W5 (slot design). A "kernel only" control cell is a wasted ladder slot: the simulator can measure the
control; the ladder should carry three cells that are each a best guess under a different assumption
about the field.

W6 (1.5 calibration list). Missing: the counting convention test above (it decides C), whether
`[rdi+100]` is really zero on the live engine (the whole lock exits through it), whether `rep` counts
once or per iteration (a rival could use `repne scasb` on VIEW_CELLS), and the sandbox board size.

W7 (R10 / X11, memory copy). "Clear any lock byte before a split so children never inherit it" is
unnecessary with a self-checking lock and harmful with the post variant, where the inherited lock is
what makes a breach column keep advancing (3.4). Keep the lock across splits; verify only that the
copy includes the parent's same-call writes.

Decisions I checked and agree with: R1-R7, R11-R13, S1, S3, S5, S6, S8, S9, S11-S13, X1-X3, X5-X10,
X12-X15, and the retirement of Tide and Reaper. R8's "emergency feed only if the simulator shows deaths"
is fine. R14's conveyor can stay parked.

## 3. What wins against a strong human field

### 3.1 The grab (measured)
One kernel-like colony alone on 64x64 (split at e>=5 into the first empty neighbour, else rest; floor
rounding): population 27 at tick 25, 84 at 50, 284 at 100, 606 at 150, 1037 at 200. That is a quarter
diamond of radius r with r^2/2 cells: r = 24 at tick 100 and 45 at tick 200, so the splitting front
moves 0.23 squares/tick, below the 0.33 estimate (floor rounding leaves 2-energy children that need 3
rests). Contact between adjacent corners therefore comes at tick ~135, the centre at ~270.

Two colonies with speeds v1, v2 meet at 63 v1/(v1+v2) from the faster corner. A MOVE scout is 1.0
squares/tick. A scout that leaves at tick 15 and plants at distance 20 at tick 35 has a nucleus whose
front is 20 + 0.23(t-35) from home; the enemy's main front is 63 - 0.23 t. They meet at t ~ 140 and
x ~ 44 instead of 31.5: +12 squares on that axis. A centre scout (62 steps, arrives ~tick 75) grows a
diamond that the corner fronts only reach around tick 170; its radius by then is ~20, roughly 600-800
squares taken from all three opponents at once. If every strong rival does the same, the centre is a
melee of 2-5 energy cells at tick 75-100, decided by initiative (section 3.2) and by who planted first.
Either way the colony with no scouts loses that land. Frontier length is what the grab buys: k separated
nuclei have roughly k times the frontier of one diamond until they merge.

The simplest feed-assist (feed a friend below 5 from e>=10) did almost nothing in the run above (290 vs
284 at tick 100) because interior cells rarely hold 10 before tick 60; a real assist has to be designed
around the fat-burst pattern (a 20-energy tip splits 3 squares in 3 ticks) and tested, not assumed.

### 3.2 Front duels (measured)
Setup: 20x16 board, 160 cells each side in two 8-row blocks, attacker eats at 5, defender eats at 6;
each side's slow path (split into empty, feed, rest) at 25. Defender populations:

| Defender | start energy | t=100 | t=200 | t=400 | t=500 | ~t=900 |
|---|---|---|---|---|---|---|
| no feeding | 20 | 90 | 33 | dead | | |
| no feeding | 50 | 105 | 52 | dead | | |
| feeds (e>=14, margin 4, poorest friend) | 50 | 160 | 160 | 160 | 146 | 56 |
| tie 6 v 6, no feeding | 20 | 162 | 161 | 164 | 164 | stable |

Readings. A strictly faster front against a non-feeder takes ~3 rows per 100 ticks (one 50-energy cell
lasts 25 ticks but its refills are 2-25 energy children). Against even a naive feeder it takes nothing
for 400 ticks and then ~1 row per 100 ticks as the defender's energy runs down (the defender's total fell
from 6420 to 4218 during the "zero loss" phase: a capped interior earns nothing, so the brigade was
running on reserves). A tied count is a zero-drift random walk: no land moves in 500 ticks. Scale to the
ladder: a 32-row quadrant behind a 60-cell front needs ~120 energy/tick of feed; at one energy per
resting producer per tick plus relay ticks that is roughly 300-400 of ~1000 cells busy, affordable
against one faster neighbour, marginal against two. A good feeder loses only part of a quadrant by tick
3000 to a 5 against its 6; a non-feeder loses it all by tick ~700 after contact.

So in the strong field the realistic picture is: tied fronts and fed fronts freeze; unfed fronts
collapse; breakthroughs happen where geometry gives 2:1.

### 3.3 Stun geometry
A straight front is 1:1 and a diagonal front (x+y = k) is 2:2 with a perfect matching when every cell
bites the same relative direction; the fixed order D,L,U,R gives that matching for each of the four
diagonal orientations (each cell sees the same pair and picks the same first). A salient cell (three
enemies, one friend behind) breaks the fixed order: with enemies U, L, R it bites L, which its row-mate
below already covers, and the cell ahead is left free to act. Rule for three enemies: bite opposite the
friend side (table-encoded, still 6).

After one kill and one refill the geometry flips: our new cell at the breach touches three enemies,
and each enemy flank cell now touches two of ours (the breach cell and its row-mate). 2:1 drains 4/tick
against at most 2/tick of feed from one back cell, so a fed front unzips from the first breach outward.
That is why the first kill and the refill race (3.4) matter more than the per-cell attrition rate.

### 3.4 Logistics and the refill race
After our front cell kills its target at the start of a tick, the square is free next tick for whoever
acts first with a SPLIT or MOVE into it: our killer (now with no adjacent enemy, so F6 misses and it runs
the slow path), or the enemy's back cell behind the dead one (its slow path; its flank cells are stunned
by our row-mates if we are faster). A lean rival's split path is 10-12 (Hunter's is 20; ours is planned
at 20-40). With the post lock the killer's refill is 5 and wins every race, and the child inherits the
lock pointing at the next enemy row: a breach column that keeps eating and refilling at 5 as long as it
has energy. Without it, every kill against a lean rival becomes "they refill with a 3-energy child, we
eat it in two ticks, repeat": +2/tick for us, no land.

Feeding rules that follow from 3.2: feed is the defence, so (a) second-row cells feed the front every
tick it is below 48 (stunned front cells cannot feed or rest, only receive), (b) producers must be kept
below 50 by feeding forward early (a 50 rests for nothing), (c) relays never feed from <=4, (d) the
front cell must never sit at <=2 when the bite lands (a 3 survives: 3 -> 1 -> fed 3).

### 3.5 Endgame
Only population counts, then energy. From ~tick 2950 energy has no future value: stop long-range
feeding, keep front cells >=3, fill every hole. Last-tick children next to an enemy count only if >=3
(a newborn is on the board at once and a slower enemy bites it the same tick). A split at tick 2999 with
a 2-energy child next to an enemy is a gift. Interior energy is a tie-break only at equal population,
which happens mainly between copies of the same bot.

### 3.6 Four-player dynamics
Each colony has two edge neighbours and one diagonal one met only at the centre. Points are by rank
among the living; being alive and smallest is 0, the same as dead. So the floor is "bigger than one
living rival", which the bots give for free when present (Idle is one cell; Medic and Walker stall at
~6 energy per cell and never eat), and the real contest is 1st/2nd among the humans. The two colonies
adjacent to a bot's quadrant race for its 1024 squares; scouts and a fast grab win that race, fronts
decide nothing there. A colony that dies feeds both neighbours; keeping a front frozen (feeding) while
a neighbour on the other side is eaten by someone else is the common "finish second" shape, and the
scout into the dying quadrant is the way to turn it into first.

## 4. The trio

A/B/C are not the right three. A is a control the simulator can measure; C is A plus one feature that
should be shared; only B is a bet. Proposed: one kernel (F6 + post lock, scouts, brigade feeding,
table-encoded multi-enemy, fast refill, endgame fill) and three settings of the parameters the ladder
must settle because they depend on the field:

**Hold** (bet: rivals are at <=5 or feed well, so fronts freeze and defence plus land decides). Two
scouts (centre, one edge midpoint), prey rule child >=8, refill only when the parent keeps >=8, strongest
brigade (producers feed forward from e>=12, second row feeds the front every tick it is <48), no pushes.
Loses least against blind-lock rivals; gains least against weak ones.

**Spore** (bet: the grab decides, the centre and dead quadrants are the prize). Four scouts (centre,
both edge midpoints, one toward the diagonal corner that plants at distance ~25), feed-assist from
e>=8 to a friend with an empty outward neighbour, split threshold 5 everywhere outside enemy view, a
second scout wave at tick ~150 from any front cell that sees no enemy within the 5x5 and has e>=12
(claims land left by dying colonies). Moderate brigade.

**Breach** (bet: most rivals at 6+ do not feed well, so kills convert). Post lock with inherited column
advance, refill with any child >=3 when the killer is locked, three-enemy rule, 2:1 seeking on the slow
path (split or move to touch an enemy that a friend already touches, only when e>=10), feeding routed to
locked cells first; two scouts. Highest ceiling against Hunter-class and lean humans, bleeds against
blind locks.

Before any of these is ready, upload a **Sprint** cell (F6 + split into the first empty at e>=5 + rest,
about 30 lines, every path under 12) to one slot to collect match pages. Replace it when Hold is ready.

## 5. Missed

5.1 **The floor is 3, not 5.** `or al,[rdx] / jz / ret` with rax = 0 at entry ("Registers ... are reset"
suggests zeroed; verify) is a permanent blind lock at 3. Its failure modes: bites air for ever once the
target dies (no income, no refill, but it still holds its square), bites a friend that moves in, ignores a
second enemy on another side. On a defended front none of that matters: a blind-3 line freezes every
rival at >=4, and the defender cannot touch it. A strong human can find this in an hour. Our 5 loses
every pair to it and must fall back on feeding (3.2). No cheaper exit exists: any test adds 2, so 5 is
the floor for a lock that can exit; 4 is a blind lock without the rax assumption. Decision needed: is a
blind-3 slot (Breach variant) worth its land-conversion loss? Only after reading rival counts.

5.2 **Unused view bytes as sentinels** are an ABI dependency: a later engine version that fills bytes
89-127 would turn every one of our locked cells into a bad target read. Check ABI_VERSION at build time
and prefer the `VIEW_W` sentinel (offset 12, value 64 on the ladder, never 0..3) over byte 100.

5.3 **Capped cells earn nothing.** A packed interior at 50 is zero income; the colony's real income is
the number of resting cells below 50. Every feeding rule should keep producers cycling below the cap.
Total-energy tie-breaks are irrelevant; income is not.

5.4 **Stun blocks feeding.** A front cell that is bitten first can never feed, so front cells cannot be
relays and a two-sided front (two faster neighbours) has only its diagonal-back cells as feeders.

5.5 **The split child is sized at the parent's turn, not at Decide.** A feeder with a shorter path than
the splitter acts first, so a 4-energy frontier cell fed to 6 the same tick splits 3/3 instead of
failing. Make the feed path shorter than the split path (it is a slow-path ordering, free to arrange).

5.6 **`repne scasb` over VIEW_CELLS** finds an enemy byte in one instruction if `rep` counts once;
with the setup it is ~7, no better than F6, but a rival might use it and the calibration should include
one `rep` cell so the simulator's counts for rivals are not fiction.

5.7 **Source limit 64 KB and the prepended header.** The server prepends `bits 64 / org / default rel`;
a second `org` is a NASM error. Generated tables must be compact (`times`), and `nasm -e` output must be
checked for size before upload.

5.8 **The jump table must never be entered with an impossible mask.** It cannot be with `pmovmskb` on a
16-lane compare (max 0xFFFF > 1105): kEnemy's 0xFF lanes guarantee bits outside {0,4,6,10} are zero
only if the view bytes are 0..3. If VIEW_CELLS ever held 0xFF (it does not per the docs), rax would
exceed the table. Cheap insurance: `and eax,0x451` costs one instruction; instead size the table to 65536
qwords (512 KB, too big) or accept the documented range. Note it as an accepted ABI dependency.

5.9 **Fault risk list is still short.** Add: `movsx`/`movzx` of [rdx] when another path wrote a role
byte at offset 0 (layout discipline: the lock byte owns offset 0 in every design, including A and B);
`jmp` to a table entry that is a label in a `%ifdef` block not assembled for that design (link-time
zero); stack use (none needed; any `push` needs its `pop` before `ret`).

5.10 **Who bites the newborn.** Our 10-11 first-contact tick means the enemy's fresh child at 6 bites
first once. Cost 2 energy, and nothing more if the lock byte store happened in Decide (stunned cells'
memory writes persist, to verify). If that assumption fails, the lock never engages on cells that are
stunned on first contact, and the whole design degrades to F6 with a +3 tax. This is the single most
important sandbox fact for C and for the kernel.

5.11 **Placement is by rank among the living**, so a colony that has lost its war should not try to
"survive longer" (no points for it unless another colony also dies); it should keep as many cells as
possible for as long as possible, which the same code already does.

## 6. Simulator experiments (decision-relevant, in order)

E0 **Rival set** (prerequisite). R-F6 (6 flat, split@5 into first empty, rest; slow paths 10-12),
R-Post5 (our post lock), R-Blind3 (permanent blind lock, F6 full path, no feeding), R-Feeder (R-F6 plus
second-row brigade), R-Grab (R-F6 plus feed-assist and 2-4 scouts), R-Static (corner-tuned static order,
4-10), R-Hunter+ (Hunter that only splits into empty squares, 10-14). Each as a Python policy with
path-tagged counts and a no-taken-jumps third value.

E1 **Frozen front.** 20-wide straight front, 8 rows deep each, attacker R-Post5 or kernel, defender
R-Feeder at 6 with the brigade variants (producer floor 10/12/14, second-row every-tick feed on/off),
1500 ticks, rows lost per 500 ticks and defender energy. Changes: the weight of feeding in the kernel
and whether Hold or Breach gets the aggressive parameters. Already indicated: naive feeding holds 400
ticks (section 3.2).

E2 **Scouts and grab.** Four-way mirror of the kernel with scouts {0, 2, 4, 4 + centre} and
feed-assist {off, e>=8, e>=10}; area at ticks 100/200/300 and final placement when one variant plays
three others; also with one slot replaced by Idle (dead-quadrant race). Changes: scout count and
bearings in the kernel, and whether Spore keeps a slot.

E3 **Refill race.** Front with the attacker at 5 against R-F6 (split path 10) with our refill at
{5 post, 15, 25}; land gained per 100 ticks after first kill. Changes: post lock vs checked lock, and
the prey threshold on refills.

E4 **Multi-enemy handler cost.** Breach and salient setups against R-F6 and R-Static; handler at 6
(table direction, three-enemy rule) vs 16 (kill-first). Changes: W2.

E5 **Convention flip.** Rerun E1 and E3 with `--order-no-taken-jumps`. Changes: whether C (and the
lock in the kernel) exists in that world; what the first sandbox upload must measure.

E6 **Blind-3 rival.** Kernel vs R-Blind3 with full feeding: land lost by tick 3000; and R-Blind3 vs
R-F6 to see how much land the blind lock itself loses by never refilling. Changes: whether a blind-3
Breach variant is ever worth a slot.

E7 **Bot exploitation.** Kernel against packed Hunter, Medic, Walker colonies from contact: ticks to
eliminate; and whether pausing to eat them beats grabbing the other way. Changes: push and refill
thresholds, scout wave 2 timing.

E8 **Endgame.** Stop-feeding tick {2900, 2950, 2990}, fill start {2960, 2980, 2995}, with and without a
faster enemy adjacent: population delta. Changes: the three constants.

E9 **Full mixes.** Hold/Spore/Breach each against three draws from {bots, R-*}, slots rotated, 50
seeds, mean points. Run last; it is the only one whose result is a ranking of the trio.

## 7. Recommendations before any data

1. Kernel = F6 miss path + post lock (5 locked, 5 refill), multi-enemy encoded in the fight table at
   6, no energy reads on any hot path.
2. Scouts in the kernel: two minimum (centre and one edge midpoint), leaving at tick 10-20 with 5-8
   energy, planting at distance 20-25 or on first enemy sight.
3. Feeding as defence: second row feeds the front every tick it is below 48; producers feed forward
   from e>=12 so nobody sits at 50; never feed from <=4; never let a front cell be at <=2.
4. Prey rule child >=8 near enemies, except a locked killer's refill (>=3).
5. Endgame constants: stop long-range feeding at 2950, fill from 2980, last-tick children only if >=3.
6. Upload Sprint now; read rival averages and the bot mix from match pages; write round 3 against that.
7. First sandbox session, in this order: counting convention (three calibration cells), rax at entry,
   [rdi+100] and VIEW_W values, memory persistence when stunned, child memory timing, split rounding,
   slot-to-corner mapping, board size and tick limit of the sandbox.
