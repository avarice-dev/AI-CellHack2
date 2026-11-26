# Review r1 - strategy and adversarial play (2026-11-07)

> **Update 2026-11-08 (docs re-review).** This is a historical record; its open questions are kept as written. A later full re-read of `docs/` settled several of them: every instruction counts, including taken jumps and `ret` (Reference p.3); energy is capped at 50 in the Tidy step (Rules p.1); feed gives 2 of the feeder's energy to any cell in that direction, so "fed +3" is feed 2 + rest 1, with no bonus (Rules p.1-2); a square freed by a death opens next tick, one freed by a move opens the same tick (Rules p.2); matches are deterministic from the seed (Rules p.3); SSE2 and SSE3 are available (Reference p.3); loops, the stack and `[rdx]` memory are allowed by the game. Ladder starts are not corners (replays; the Rules never say corners). See `architecture/overview.md` for the current summary.

Lens: game theory, energy economics, front geometry. Sources: the three doc PDFs (text extracted), cellhack.inc, designs.md.
All numbers are back-of-envelope; items marked VERIFY need the sandbox.

## 0. Summary of the position

1. The game has one dominant variable: the instruction count of the "enemy adjacent -> eat" path. Whoever is strictly lower on a front
   stun-locks every pair it touches. Land grab is second. The 2800-tick attrition is decisive only through that variable; otherwise it is a random walk.
2. Fights cannot be declined. An adjacent enemy bites whether you like it or not; you can only choose whether to extend contact
   (split or move next to an enemy) and how to supply the front. This hollows out Tide's "hold here, push there" idea.
3. A and B have the same front path and almost the same behaviour. C is the only structurally different design, but its differentiator (raiding) is the weakest part;
   its lock belongs in the shared kernel.

## 1. Arithmetic

### 1.1 Duel and front drain

- Stun-lock (one side strictly faster, 1:1 front): loser's front cell -2/tick, winner +2/tick (capped at 50, surplus lost).
  A 50-energy cell dies in 25 ticks. A feeder behind it can cancel the loss at 2/tick, but only from stored energy.
- Lane reserve under Bastion rules: feed needs donor e>=20 and margin >=4, so energy only flows through cells above 20 and each link needs 4 of gradient
  (max ~12 links between 50 and 2). Reserve above 20 in 12 cells = 12 x 30 = 360. At 2/tick that holds one stun-locked front cell for ~180 ticks.
  After that the rows fall at about one per 25 ticks (a 50-energy cell at 2/tick). 2800 / 25 = ~110 rows, far more than the 32 rows of a quadrant. So one strictly
  slower colony loses its whole quadrant before tick 3000, starting from first contact at ~tick 100 (roughly 900 ticks for 32 rows).
- Sustained supply from income: a donor makes +1 per REST, so one 2-energy feed costs 2 rest ticks plus 1 feed tick = 0.67 energy/tick per donor, and every relay hop
  spends a full action. A stun-locked front cell (needs 2/tick) ties up ~3 donor cells plus relays. For a 30-cell front that is ~100-150 interior cells doing nothing
  else. Affordable (10-15 percent of ~1000) but only with pipelined lanes, not margin-4 diffusion.
- Free transport: a cell at 49-50 wastes its REST, so feeding from it costs nothing. Capped donors should feed at margin 2, not 4.
- Equal count (coin flip each tick, independent per pair): each side's energy does a +-2 random walk. Expected absorption time from 25/25 is (25/2)^2 = ~156 ticks.
  Mean drift 0. The cap hurts the leader slightly (surplus lost). So tied fronts barely move, and the side with deeper fed reserves wins slowly.
- Exact ties between different programs are unlikely. Counts of 6 and 7 are not a 50/50 duel; they are a 100/0 duel.

### 1.2 Expansion front speed (squares per tick along one axis)

Assumes the child gets 2 or 3 of a 5-energy parent (VERIFY rounding).

| Policy | Ticks per step | Speed |
|---|---|---|
| Rest then split at 5, child gets 3 | 2 rests + 1 split = 3 | 0.33 |
| Same, child gets 2 | 3 rests + 1 = 4 | 0.25 |
| Split threshold 6 (the quick-start example) | 4-5 | 0.2-0.25 |
| Feed-assisted: rich cell behind feeds the new child +2 next tick (3+2=5, split on t+2) | 2 | 0.5 |
| Fat burst: a cell with e splits down a line, halving each step (50 -> 25 -> 12 -> 6 -> 3 is 4 steps in 4 ticks), then recharges 2-3 ticks | ~7 per 4 steps | 0.5-0.6 avg |
| MOVE scout (no energy cost, no split) | 1 | 1.0 |

Contact between adjacent corners (63 squares apart, meeting near 31): naive 31/0.33 = ~95 ticks; feed-assisted 31/0.5 = ~62.
Centre (Manhattan 62 from each corner): naive ~190 ticks, feed-assisted ~125. Quadrant packed by roughly tick 250-350. This matches "~200 ticks".

Where the border settles when speeds differ: border distance from own corner = 63 x v1/(v1+v2). Equal: 31.5. 0.5 vs 0.33: 38 (+6.5 columns, ~+20 percent of that
quadrant edge). A scout planting a nucleus at distance 20 by tick 20 puts that nucleus's front 20 - 20/3 = ~13 squares ahead of the main diamond for the rest of the
grab (if it is not eaten): border about +10 squares on that edge.

Vacant bot quadrant: Idle is one cell. The 1024-square quadrant goes to whoever arrives first, shared between its two neighbours and the diagonal colony.
Taking +300 squares of it is worth more than any border shuffle with an equal opponent.

### 1.3 Which is more decisive

| Situation | Decided by |
|---|---|
| Opponent front path strictly slower (Hunter probably, most first drafts) | Attrition, completely: ~900 ticks to eat a quadrant. Grab only sets the start line. |
| Opponent front path strictly faster | Attrition, completely, against you. Nothing in A/B/C recovers this. |
| Exactly tied (clones, locked mirrors) | Grab (+-20 percent area) plus reserve depth. Attrition is a +-2 random walk and almost neutral. |
| Opponent passive (Idle, Medic, Random, Walker) | Grab: speed into vacant land; then front cells eating wins by default. |

Answer to design question 3: the 2800-tick phase is decisive only through initiative, and then it is overwhelming. If initiative is tied, the first ~200 ticks decide.
So: (1) get the front path to the floor, (2) maximise grab speed, (3) logistics and push rules are tertiary.
The draft ranks them the other way round (A/B differ in logistics and sensing, nothing in the front path).

## 2. How each design loses

### Design A, Bastion

1. Variable front path. Static order 4/6/8/10 is direction dependent; average 7. The directions the enemy actually comes from differ by corner (top-left meets Right
   and Down, i.e. 6/8 or worse), so a tuned opponent at 6 stun-locks every A cell whose enemy sits at Left or Down. Fix: a flat path (SSE2 7, or the table versions in
   section 4) or a corner-specific order via a stored jump.
2. Feed throughput. Donor e>=20 and margin 4 gives reach ~12 and only ~360 stored energy per lane. Against a faster eater a lane lasts ~180 ticks then falls.
   It cannot win that matchup, but it lasts longer if capped donors feed at margin 2 and the e>=20 donor floor is dropped.
3. Grab. Feed starts at e>=20, which deep cells reach only after ~tick 60-100, so the grab is unassisted (0.33). A feed-assisted opponent reaches contact at ~62
   against A's ~95 and takes ~+6 columns on each shared edge. Fix: during the grab, cells with e>=10 feed a friend that has an empty outward neighbour.
4. Standoff gap. Threshold 16 whenever an enemy is within 2 squares means that when fronts meet with a one-square gap, neither side fills it until a cell is fat. A
   Hunter-like colony with a lower threshold fills the gap with 2-3 energy children, which then bite first if their count is lower. The gap is also unpaid score.
5. Vacant-quadrant race against an opponent that plants nuclei early: loses ~10 squares per edge.
6. Matchups. Hunter: wins if Hunter's eat path is longer (read hunter.asm; a 4-direction loop is probably 15-30). Idle, Medic, Random, Walker: wins; Walker cells wander
   into A's line as free meals (+2 each). Tuned human hunter with a strictly lower count: loses everything, slowly (~900 ticks). Same flat count: coin flip, even,
   decided by the grab.

### Design B, Tide

1. Sensing is on the front path. Last action / last energy must be stored every tick on exactly the path where initiative is decided. Two to four extra instructions
   hand initiative to A in every duel between them: B loses to A head to head. Fix: sense on the slow path only from stateless data (my energy vs the enemy neighbour's
   energy in VIEW_ENERGIES needs no history), or sample on a tick mask (still a flat +2).
2. Nothing to do with the result. A cell that learns "I lose initiative" cannot disengage: a stunned cell cannot move, and an unstunned one usually has no free square.
   The levers are (a) do not extend contact (already A's prey rule) and (b) feed it more (a priority tweak). The 5x5 strength sum is mostly noise at a front: 25 squares hold
   ~10 friends and ~10 enemies and who is in view dominates.
3. The learned score spreads "along the lineage", but front cells' children are born behind or beside them; lineage is not the front. Inherited information is stale within tens of ticks.
4. The objective is rank (3/2/1/0), not share. POP_ENEMY/3 compares you with the average of three opponents; the useful comparison is with the second-best one, which the view cannot give.
5. Same grab and same front-path weakness as A, plus a long slow path. Against the bots it plays like A; against a tuned hunter it is A minus 2-4 instructions.

### Design C, Reaper

1. Raid economics are poor. A raider at 16 meets early frontier cells at 2-3 energy: it kills about one per tick (a bite kills at <=2; at 3 it takes two), but two or three
   unstunned neighbours each bite it for 2. Net about -2/tick, so it dies after 3-5 kills, having cost 16 energy (about three splits) and its rest income. The freed square is
   refilled by neighbours in ~3 ticks. That is break-even at best and, in a four-player game, feeds the third and fourth colonies. A walking raider also runs the long logic
   path, which is slower than Hunter's eat path, so a Hunter front cell bites it first and stuns it.
2. Mirror. Two Reapers fighting lose to Bastion or Idle in the same match; aggression only pays against a victim that is weak anyway, and A beats those too.
3. The lock's gain is small. Blind lock is 4 (dispatch 2 + mov + ret); with any exit rule it is 5-6. Against a flat 7 that is decisive; against a tuned 4-5 it is nothing.
   A stateless branchless post (section 4) gets 4 with no dispatch and no modes, so the lock does not need the mode machinery.
4. Blind-lock failure modes: the target dies and the cell wastes every tick (no rest, no refill) until the exit fires; a new enemy arrives on another side and the locked
   cell ignores it; cells locked on the same target double up while neighbouring targets stay unstunned.
5. The +2 dispatch applies to the refill path after a kill, where the count again decides who takes the freed square.
6. The fallback (to Bastion when POP_SELF < POP_ENEMY/3) fires on noise before tick ~30 when populations are tiny, and again when raiders have spent the reserve.
   It needs a minimum tick and hysteresis.
7. Matchups: strong against Idle/Medic/Random/Walker (but so is A); against Hunter wins if its path is longer (so does A); against a tuned hunter loses its raiders, then
   behaves as A with extra overhead.

## 3. Ladder slots

A and B are ~80 percent the same program, and B's addition costs initiative. C is different but its main idea (lock) is shared infrastructure. Three such slots mostly
measure the same thing three times.

Proposed trio (one idea per slot):
1. Bastion-Fast: A on the best flat or branchless front path, feed-assisted grab, kill-and-refill. The control.
2. Bastion-Spore: slot 1 plus scouts that plant nuclei, plus the cheapest form of Tide's push (refill a freed square; prefer targets <=2). Tests the grab.
3. Reaper-lite: slot 1 plus the stateless post lock and opportunistic hits on <=2-energy targets, no walking raiders. Tests aggression at small cost.

Alternatives: Spore is not a separate design; it is a ~30-line opener for all of them (its stated cost, "seeds earn nothing while walking", is minor: interior cells at 50
waste income anyway, and a scout carries its own 5-12 energy). Lattice: reject; 20 percent holes cost 20 percent of final population for a mobility benefit that feeding already
provides. Turtle: reject; land is score. New candidate: Sprint, a tiny program (<10 instructions on every path, no memory, no init) as a control and a fallback if the sandbox
shows that bigger programs lose fights.

## 4. Cheap, high-value tactics missing from all three

1. Branchless post as the shared front path (4 instructions, no branch, stateless apart from a stored direction):
   `movzx ecx, byte [rdx+4]` / `movzx eax, byte [rdi+rcx+VIEW_CELLS]` / `mov al, [rdx+rax+8]` / `ret`, with a 4-entry action table at [rdx+8..11] indexed by cell type
   (empty -> split or rest, friend -> rest, enemy -> eat+d, wall -> rest). A one-direction version with an absolute table in code is 3. For all four directions the SSE2
   path is 6-7 flat. Pick by the measured counts of the opponents (VERIFY whether ret and taken jumps count).
2. Scouts from tick ~15-25 using cells with e>=12 (they carry the 5 needed to plant). MOVE is free: frontier speed 1.0 vs 0.33.
3. Feed-assisted grab (e>=10 donors toward cells with an empty outward neighbour): 0.33 -> 0.5.
4. Kill-and-refill speed. A freed square is entered next tick by whoever has the lower count. Table entry EMPTY -> SPLIT+d gives the refill on the same 4-instruction path.
   Each refill is a 2-point swing in population.
5. Consistent bite direction and lowest-energy-first targeting. On a diagonal (diamond) front each cell touches two enemies; if every cell bites in the same relative
   direction the bites form a perfect matching and every enemy cell is stunned; mixed directions double up some targets and leave others free to bite back. Lowest energy
   first is a free Schelling point for focus fire.
6. Free feeding from capped cells: a cell at 49-50 wastes its rest; feed at margin 2 from capped donors, margin 4 from others.
7. Drop the init step. VIEW_COLONY (0..3), or x/y vs W/2,H/2, already gives the corner; no memory write on tick 0. (VERIFY the colony-to-corner mapping.)
8. Read hunter.asm for its front count, split-direction preference and fat threshold. If it fills in a fixed direction order its quadrant has thin gaps: a planned target.
9. Endgame beyond fill: stop feeding in the last ticks where it cannot change a death before tick 3000, and in the final ticks front cells with a <=2 target eat, then
   split into the freed square the next tick if one remains.

## 5. Rules and assumptions to correct or verify

- Section 1.1 point 2 ("growth is limited by free squares, not by energy"): true in the packed interior, false at the front, where it is energy per cell (5 to split, child at
  2-3, 3-4 ticks per step). That is why feed-assist and scouts help.
- A newborn acts from the next tick and its count decides initiative like any other cell. A 2-energy newborn with count 4 next to a 50-energy cell with count 8 stun-locks it.
  Energy does not protect against a faster cell, only against a quick kill. The prey rule means "do not give the enemy a free kill", not "do not give it a duel".
- A feeder with less than 2 gives all it has and dies; keep the donor minimum >=4.
- VERIFY: split rounding (0.25 vs 0.33 speed); whether energy above 50 mid-tick can be spent; counting of ret, jumps and rep; colony start squares; Hunter's source and count.
