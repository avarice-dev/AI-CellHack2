# Round 3 review (Claude) — designs.md against ladder pulls 1 and 2 (2026-11-08)

Read: `data/ladder-data-2-2026-11-08.md` and `designs.md` in full; `data/pull2/validation-table.md`,
`winrates.json`, the 36 per-replay summaries (`data/pull2/summaries/*.json`, queried with three short
single-process Python scripts kept outside the repo), pull 1, the site observations, `cells/sprint.asm`,
the Rules and Reference pages, `cellhack.inc`, and my r2 review with the lead's F1-F20 decisions. Per the
user's scope change the simulator code was not reviewed and job 5 is a short list of design questions.
Counting convention: every executed instruction, taken jumps and `ret` included (verified on the site).

## 0. Verdict in ten lines

1. Sprint does not lose to HammerSpb on bite order. It loses the **refill race**: in 99239 Sprint bit
   168,555 times, killed 13,853 AtomPush cells, refilled ~150 squares and gained none; AtomPush refilled
   16,601 times with 5-7-energy children. Same in 99134 (12,788 kills, 14,956 refills). The 5-instruction
   refill of the post lock is therefore the kernel's main feature, not Scourge's bet.
2. The "unexplained" +1 and +3 are REST. Rest is not an event in the replay, so an idle cell below the
   cap shows +1 and a fed cell that also rests shows +3. Nothing is missing from the rules; the field's
   realised income is 8% of cell-ticks because most cells are capped, feeding or stunned.
3. Two thirds of all bites in the data (94% of Sprint's) land on an eater at 50 and yield nothing.
4. Dogma's two premises are gone: only 2 of 36 matches are frozen by t500, and the deep pump loses to
   HammerSpb 81% of the time, to Sprint 0/11 (Aegis), and spends 85-92% of its cell-ticks feeding.
5. The lock is still right, but for the refill, not the bite: every rival is 4 in exactly one direction,
   so Sprint's flat 6 already wins two directions and ties one. A flat 5 wins three; nothing wins the fourth
   except a blind 3, which cannot refill. Post lock at 5 in every slot; checked lock and pre-arm dropped.
6. The grab is worth more than the plan gives it: the t200 leader wins 22/36, the t500 leader 28/36.
   HammerSpb, Noob+ and Aegis reach 300-440 cells at t50 against Sprint's ~245; zergling reaches 1857 at
   t100 by moving. Contact comes at tick ~37, so scouts are the wrong grab tool; movers and assist are right.
7. Refill child size decides conversion: pumps refill with 2-3 (one bite), HammerSpb with 6-7, Sprint
   with 8. That is why Sprint eats pumps and freezes against HammerSpb.
8. Trio: Scourge (conversion), Contagion (grab, same kernel), Sprint stays until both have 50 games.
9. No new replay downloads are needed; the 35 stored replays answer the next questions offline. The one
   probe worth a ladder slot is the first kernel cell itself (4 or 5 in rivals' fast direction).
10. Top unknown is unchanged: whether a stunned cell's memory write persists. It is detectable from our
    first kernel cell's first replay.

## 1. What pull 2 changes in designs.md (job 1)

W1 (section "What changed" item 2, 2.1). "The best rivals bite in 5 or fewer ... the lock is no longer an
option." The 63-of-88,183 figure is one match where Brawler's UP (its only 4) faced Sprint. Pull 2, 36
replays, every strong rival: one direction at 4, at most one at 6, the rest >= 8 (Aegis, Noob+, Noob++
have no 6 at all). Against that profile a flat 6 wins 2 directions, ties 0-1, loses 1; a flat 5 wins 3,
loses 1; only a blind 3 wins 4. The lock converts a tie into a win on one side and never touches the 4.
Its real value is the 5-instruction refill (W2). The sentence should read: "the lock is kernel because
it refills at 5".

W2 (2.1 table, 3). The refill is priced as "slow path ~20" for Dogma/Contagion and 5 for Scourge, as if
it were a bet. Data: Sprint's slow-path split is 19-21 and it won essentially no refill race against
AtomPush or AtomCrasher (99239: 1522 births for 1370 cells of growth and 179 deaths, i.e. ~150 refills
against 13,853 kills; 99134: 2368 births, 449 deaths, ~2169 growth; 99413: AtomCrasher 3779 deaths, 5442
births; 99420: 8082 / 9753). So HammerSpb's split path is <= 20 (their average 35 is the feeding tail).
Arithmetic of the stalemate: AtomPush's refill child is 6-7 (parents 12-15), Sprint kills it in 3-4
bites, AtomPush refills again: AtomPush pays ~7 energy per 3-4 ticks per contact cell (~35/tick for the
whole front, covered by ~5% of 2700 cells resting), Sprint gains 0 (capped) and 0 squares for 2700 ticks.
A refill at 5 beats every measured split path, so each kill becomes a square; a refill at ~20 beats none.
Consequence: the post lock goes into all three slots; the checked lock has no measured use (W3).

W3 (2.1 "pre-arming"). Pre-arming saves the first-contact cost (5 instead of 10-11) once per contact,
i.e. one bite of 2 energy, and only against the rival's 6 or 8 directions (against its 4 we lose first
contact anyway). It buys nothing measurable and it rules out the post lock. Drop it.

W4 (1.2, 2.4 "D ~ 6 Brawler-like"). Pump economics as measured: Brawler, Bouncer, Noob+ feed in 85-92%
of their cell-ticks (Brawler v2 88%), 66-88% of those feeds go from a cell at 5-9 to a cell at 3-7
(diffusion among thin interior cells), so they rest in at most ~12% of ticks and their colony energy is
8-20 per cell; the front is fat (31-49) from its own bites, not from feeding. The pump beats HammerSpb
only when it is ahead on land at t200 (98854: 2530 vs 1321; 99304: 2007 vs 771; 99230: 2688 vs 860;
99208: 2396 vs 922; 98843: 3165 vs 772; 98911: 2800 vs 414) and then grinds a 50-energy colony whose
bites are wasted. Over the field the pump loses: HammerSpb 73-77% wins; Bouncer 56%, Brawler v2 52%,
Brawler 43%, Noob+ 37%, Aegis 30%. Its refill children are 2-3 (Brawler v2: 6149 of 10,252 attributed
children at 2; Bouncer 5430 at 3), one bite each, which is why Sprint's flat 6 beats Aegis 11/0, Noob++
12/5, Noob+ 8/5. D = 6 reproduces the losing economy. D belongs in 12-20 (section 3 of this review).

W5 (3, Dogma's bet "fronts freeze; land at freeze time decides"). Freeze tick median 2076; 2 of 36 by
t500; post-t500 swings above 1000 squares in at least 13 colony-rows. The t500 leader still wins 78%, so
land matters, but it keeps moving for 2000 ticks through kills converted by refills and through dead
colonies' land. Dogma has no premise left; see section 4 for what takes its slot.

W6 (2.5 scouts, S = 4 for Contagion). Median closest pair of starts is 18 Manhattan (min 8); two fronts
at ~0.24 squares/tick meet at ~18 / 0.48 = tick 37. A scout leaving at tick 15-20 walks into the
neighbour. Scouts pay only from a start near an edge (49% of starts are within 9 squares of one) toward
the far side, and the far side is where the other colonies are. S <= 2, edge starts only. The measured
grab tools are different (section 2, D7): moving frontier cells (zergling 1857 at t100) and feed-assist
(Noob+ 1364-1574, Aegis 1100-1260, HammerSpb 700-1400 at t100 against Sprint's 355-954).

W7 (1.2 facts). AtomPush "bites below 6 on ~85% of contacts" was one match's mix of its R (4) and L (6);
the profile is R 4, L 6, U/D >= 8. HammerSpb "feeds ~10 per eat": AtomCrasher 6.2 pooled (1-29 per
match), AtomPush 17.8 pooled (4-300: it feeds hard only when it is losing a front). 1.3.4 and 1.3.5 are
answered (starts: median 10 from the nearest edge, uniform-looking, one start at (1,1); split: child
floor(e/2), parent the rest). The cap is 50 at Tidy; mid-tick values of 52-56 occur (receivers fed twice
before Tidy), so the sim's "cap at Tidy" default is the real rule.

W8 (2.6 endgame, 5 ladder). Unchanged and fine. Add: 14 of 36 matches end early at "last colony
standing", Sprint ended 8 of its 17 that way (ticks 808-2516); eliminating the field is a 3-point result
and no rule penalises it.

## 2. What the data shows that the summary did not say (job 2)

D1. **REST explains both unexplained effects.** Per match, the share of event-free cell-ticks that end
+1 is 2.7-3.2% in fields of fat colonies (99061, 99119, 99168, 99324, 99365, 99388: Sprint, HammerSpb,
rooby at 46-50) and 55-67% where a thin pump dominates (98790 Aegis 67%, 99208 Aegis 63%, 99304 Brawler
v2 55%). A capped cell rests for 0; a thin cell rests for +1. Receivers: +3 in 47-100% of single-event
cases, +2 in 0.1-6% (cells at 48-49, or a failed action such as a split into an occupied square), 0 when
full. No periodicity, "slightly more at e < 5" because a cell below 5 cannot split and rests. So: no
passive income exists, no feed bonus exists, and the simulator must not add either; the replay-style
statistic has to be computed with rests invisible, as the site's log has them.

D2. **Bites are income only below the cap, and the field wastes two thirds of them.** Single-event
eaters: +2 in 1.48 M cases, +0 in 2.93 M (66%). Sprint in 99239: 165,694 bites at +0, 10,594 at +2 (94%
wasted): it drained 336 k energy from AtomPush and kept 6% of it. The pump's secret is only that its
cells are below 50, so its bites count. A fat colony is a battery, not a generator: its income is the
number of cells below 50 that rest, which under drain is just the feeder chain.

D3. **The refill race is the late game.** Who gains after t500: Sprint eating non-feeders and pumps with
2-3 refills (+2987 in 98879 from rooby, +2528 in 99211 from Brawler v2/Bouncer, +2103 in 99021 from
Noob++, +1624 in 98964, +1459 in 99097); pumps grinding AtomPush from a land lead (98766 +2350, 98854
+1235, 99304 +1243, 99230 +711); rooby eating Noob++ (98862 +1587). HammerSpb never gains a large block
late except from each other or rooby. Nobody converts kills against a colony that refills with >= 6 and a
split path below theirs. Our 5-refill would be the first.

D4. **Refill child size is the fingerprint that predicts duels.** Parents at a split (fights only):
AtomPush 12-15 -> children 5-7 (a prey rule of ~12-14, 6-7 energy, three Sprint bites); AtomCrasher 10-13
and 50 -> 5-7 and 25; Brawler v2 5 -> 2 (6149 of 10,252); Bouncer 6 -> 3 (5430 of 5073+); rooby 6 -> 3;
Sprint 16-17 -> 8 and 50 -> 25. Deaths per enemy bite received, pooled: Sprint 0.016, rooby 0.014
(50-energy walls), Brawler v2 0.035, Aegis 0.037, AtomCrasher 0.067, Bouncer 0.069, Noob+ 0.10, Brawler
0.11, AtomPush 0.14, zergling 0.78. Our rule "child >= 8 near enemies" is right; a post-lock refill from a
50 gives 25 and halves a wasted battery into two productive eaters.

D5. **Direction luck is worth about 16 points of win rate.** For the 29 strong-rival pairs where one
side's fast direction pointed at the other's start and the other's did not, the fast side placed higher
in 19 (66%). Sprint faced a rival's fast direction by start geometry in 1 of 51 pairs (98964, Aegis UP;
Sprint won anyway) and lost both AtomPush matches with AtomPush looking UP at it (>= 8 against Sprint's
6): bite order did not decide them, refills did (D3).

D6. **What separates HammerSpb from the pump winners.** Not bite speed (both are 4/6/8+ static) and not
feeding depth as such. HammerSpb: fastest grab in the field (t50 300-400, t200 1300-2300), prey rule
~12-14 so refills survive, split path <= 20, feeds only when losing (AtomPush 4-300 feeds per eat by
match). Pumps: more cells per energy (4095 x 14 vs 1300 x 46 at the end of an upset), so when they get
the land lead they hold three times the population on the same energy and the fat enemy's bites are
wasted on them. Aegis is the weakest pump because 34% of its feeds hit a cell at 50 and 37% of its feeders
are at 48+ (feeding full cells is pure loss): 30% wins.

D7. **Grab mechanics in the data.** t50 / t100 populations: Sprint 127-253 / 355-954 (median ~245 /
~750); AtomPush 232-403 / 615-1249; AtomCrasher 131-335 / 345-1229; Noob+ 203-438 / 301-1574; Aegis
216-391 / 547-1262; zergling 191-473 / 392-1857 (24,099 moves in 8 replays); Brawler v2 168-350 /
313-1391; Bouncer 113-300 / 289-1118. The spread within one cell is start geometry (edge distance,
neighbours), so the sim must use the measured start distribution. The 1.5-2x over Sprint comes from
feed-assist (a boxed cell feeds a frontier cell so it splits every 2 ticks instead of 3) and from moving
(a frontier cell that cannot split steps outward for free and the interior splits into its old square).
zergling's collapse afterwards is its front (6 in one direction, thin 9-14 everywhere), not its grab.

D8. **Sprint's wins are the field's weakness, not Sprint's strength.** 15 of its 17 replayed wins are
against rivals with 2-3 refills or no feeding; its two losses are to the one colony that refills at 6-7
behind a split path faster than 21. Keep that in mind when the first kernel cell's rating is compared
with Sprint's 1243: the same field flatters both.

D9. **Mid-tick energy exceeds 50.** Receivers at 52-56 before Tidy appear by the tens of thousands
(98854: 86 k at 52). A cell at 50 fed before it splits gives a 26 child. Harmless, but "never feed a
target >= 47" is also an income rule: a feed into 48+ is partly or wholly destroyed at Tidy.

## 3. The front path (job 3)

Price per direction of contact against the measured profile (one 4, zero or one 6, the rest >= 8), plus
the refill race against a split path of <= 20 (HammerSpb) or ~21-40 (everyone else), plus the likely
counter-moves once a 5 appears on the ladder.

| Path | Bite vs 4 | vs 6 | vs >= 8 | Refill | Other paths | First contact | Notes |
|---|---|---|---|---|---|---|---|
| Flat 6 (Sprint) | lose | tie | win | slow path 19-21: loses to HammerSpb | +0 | 6 | measured: 0 squares from 13.9 k kills |
| Checked lock 5 + pre-arm | lose | win | win | slow path ~20: still loses | +3 | 5 armed, 10 not | buys one 2-energy bite per contact |
| **Post lock 5** | lose | win | win | **5: wins every measured race** | +4 | 11 | blind SPLIT on EMPTY; child floor(e/2) |
| Post lock 6 with energy guard | lose | tie | win | 5-6, guarded | +5 | 12 | gives back the 6-direction win |
| Blind 3 | win | win | win | none: bites the 6-7 refill child for ever | +2 | 9 | Sprint's freeze with better stuns |
| Static 4 in one direction | tie | win | win | needs a second check | - | 4 | one direction only: the rivals' design |

A flat 5 or 4 in every direction without memory does not exist: three instructions produce the enemy
mask, one dispatches, one sets `al`, one returns; the dispatch and the `mov` cannot merge because the mask
values (1, 16, 64, 1024) are not action bytes, and a single lock load cannot both be the action byte and
address the target square (the view offsets 39/45/49/43 are not an arithmetic progression of the action
codes 0x30-0x33 under any scale). So 5 is the floor for a lock that can exit, 3 for one that cannot.

Decision: **post lock at 5 in every slot.** Against HammerSpb it turns the measured stalemate (5 kills per
tick, 0 squares) into about one square per kill: the killer splits at 5 into the freed square before any
rival split path (<= 20) runs, the child inherits the lock and bites the former feeder at 5 from its first
turn, and the parent (now 25) is below the cap so its bites count again. Guard against the blind split from
e < 10 not on the hot path (+2 would cost the 6-direction win) but by feeding locked cells first (Scourge's
rule, now kernel) so a locked cell is normally >= 16. Measure in the first replay the share of our refills
made from e < 10.

Blind 3: keep it as the rival model of what HammerSpb or Striker may do next, not as our cell. Against a
blind-3 line our 5 never bites, but with a fed front we lose no land either; against a blind 3 that also
adds `cmp EMPTY / je split` at the top of its fast direction (a 4-instruction refill in one direction, at
the price of +2 on its own bite) we lose the refill race on that side only. Our answer, if it happens, is a
blind-3 variant of the same kernel in one slot (bite ties at 3, coin flip), not a redesign.

## 4. Slots (job 4)

The ladder allows three. Sprint holds one and is the only yardstick with a known flat 6. Proposal:

**Scourge** (first to ship; name kept: kill, refill, keep eating forward). Post lock at 5 (EAT on ENEMY,
SPLIT on EMPTY, +4 on every other path), F6 fallback at 6 plus the lock store on the first bite,
multi-enemy choice in the fight table as decided (F2). Slow path in this order: origin record; split
into an outward empty square at e >= 5 with the prey rule (child >= 8, i.e. parent >= 16, when an enemy is
in the 5x5), the split check kept under ~15 instructions because dead-colony land is a split race against
rival paths of 10-20; then feeding: never from <= 4, never to >= 47, capped donors (>= 47) feed the poorest
friend neighbour at margin >= 2 (turns a 0-income cell into a producer), donors >= 16 feed the poorest
friend at margin >= 4, a locked (front) neighbour preferred; no scouts; endgame as 2.6. Expected profile:
wins bites in three directions out of four against every measured rival, wins every refill race, holds
the fourth direction by feeding. Target against AtomPush in a 99239-like geometry: squares gained per
100 ticks > 0 where Sprint's was 0.

**Contagion** (second; name kept: spreads fast). Same kernel and feeding with D = 12. Grab phase (no enemy
in the 5x5, tick < ~200): a frontier cell with e < 5 and an empty outward square MOVEs outward instead of
resting (zergling's 1857 at t100), the interior splits into the vacated squares at e >= 5, and boxed cells
with e >= 8 assist a frontier friend that has an empty neighbour (G = 8). Movers stop and behave as
Scourge on the first enemy in view. Scouts S = 0, or 2 along the longest free axis only when the start is
within 10 of an edge. The bet: the t200 lead (61% of wins) and the dead-colony land are decided by grab
speed, where Sprint is 1.5-2x slower than the top of the field.

**Avarice (Sprint)** stays on the ladder unchanged as the third cell until Scourge and Contagion have
>= 50 games each; it is the calibration instrument for any new rival version (its flat 6 reads their
direction profile) and its 45% is the baseline both must beat. Then its slot goes to a parameter variant
of the better of the two: the feeding depth the sim cannot settle (D = 8 against D = 20), under the name
**Doctrine** (same creed, different dogma; `cell_names.txt`), or, if a rival has moved to 5 or 3 by then,
a blind-3 variant of the same kernel.

Dogma is dropped (W4, W5). The names Dogma and the slot's deep-feeding setting go to the simulator as the
pump rival model, where they describe the field's second-best strategy.

## 5. Design questions worth testing (job 5)

1. Refill: post lock 5 unguarded against a guarded 6 and against the checked lock, versus a fat feeder with
   a <= 20 split path and 6-7 children: squares gained per 100 ticks after the first kill, and the share
   of refills made from e < 10.
2. Feeding depth D in {8, 12, 16, 20} with and without "locked cells first", versus a fat feeder, a pump
   and a flat-6 non-feeder: deaths per bite received, interior energy, land at t500 and t3000.
3. Grab: mover front, feed-assist G in {8, 12} and scouts S in {0, 2}, on the measured start distribution:
   population at t50/t100/t200 against the field's 300-400 / 700-1400 / 1300-2300.
4. Counter-moves: a blind-3 rival, and a static rival with a 4-instruction refill in its fast direction:
   what the 5/5 kernel loses to each, and whether a blind-3 variant of ours gets it back.
5. Harvesting: a second-row cell that EATs its own front cell when the front is >= 48 and it is <= 46
   (+1 per tick per contact cell over resting, keeps the front's bites counting): worth its slow-path cost
   against a fat feeder over 2500 ticks? Only if yes does "Famine" become a slot candidate.

## 6. Risks, rule interactions, further data (job 6)

R1. Memory persistence when stunned is still the top unknown for the lock store (F11). It is now cheaply
observable: if our first kernel cell's bite-first share against a rival's 6-direction is ~50% instead of
~100%, the lock is not engaging. One replay of ours answers it; no sandbox work needed first.

R2. The unguarded refill. A killer at 5-9 splits a 2-4 child next to up to three enemies; the lateral ones
are stunned only if our row-mates bite them that tick. Mitigation is the locked-first feeding rule; the
measure is the share of our refills from e < 10 in our first replays.

R3. Newborns are on the board at once and can be bitten in their birth tick by any cell acting later in
the tick (Rules: "Newborns act from the next tick"; a square freed by death cannot be entered until the
next tick). Our refill child at 25 does not care; a 2-child from a thin killer dies before its first turn.

R4. Feeding from <= 2 kills the feeder ("gives all it has, and dies if that was all of it"). The rule
"never feed from <= 4" covers it; keep it in every path that can feed, including the endgame fill.

R5. Mid-tick energy above 50 (D9): a capped cell fed and then splitting gives a 26 child; a feed into a
cell at 48+ is destroyed at Tidy. "Never feed a target >= 47" is an income rule, not only a courtesy.

R6. Sentinel and table: the post lock reads VIEW_W (64 ladder, 16 sandbox) when unlocked; the 2041-byte
table with (-k) & 0xFF at every index 8k covers both. ABI_VERSION check at build time as decided.

R7. Rival adaptation. HammerSpb iterates (v7/v5), Striker runs three cells, patrickHakun uses AI. A
visible 5 invites a 5 or a 3; a visible 5-refill invites a 4-refill in the fast direction. None of these
changes the kernel; each has a one-parameter answer (section 3).

R8. Direction luck (D5) is 16 points for static rivals; it is 0 for us in three directions and remains in
the fourth. Our start geometry still decides which rival's fast side we meet, so per-match results will
stay noisy: judge the kernel on >= 50 games, not 20.

R9. Dead-colony land. Sprint's largest late gains were squares of dying colonies, taken by its 19-
instruction split against rivals at 10-21. Keep our slow-path split short and ahead of the feeding logic
(F19's "feed before split" is about the same colony's child sizing and costs us only when a feeder and a
splitter of ours meet; the inter-colony race is the one that moves land).

Further site data: nothing heavy. (a) Re-run `tools/pull2/analyze.js` offline on the 35 stored replays
for two statistics the summaries lack: who occupies a square freed by death and how many ticks later
(colony of the newborn versus the killer), which measures every rival's split-path speed relative to
Sprint's 21; and per-colony counts of event-free +1 cell-ticks, which is each colony's income per tick.
(b) The 4-versus-5 probe is the first kernel cell itself: its bite-first share in a rival's fast
direction is 0% if they are 4 and ~50% if they are 5; no separate probe cell is needed. (c) Watch the
leaderboard snapshot (40 KB) for version changes before any new replay download; download new replays
(25-53 MB each) only for a new rival version or for our own first 3-5 matches. (d) Nothing goes on the
ladder without the user's approval; the first upload is Scourge, created by the scripted POST and run in
the sandbox against the five bots first.

## 7. Suggestions (G-list, most important first)

G1 [decision-wrong] Dogma's premises are contradicted by pull 2: 2 of 36 matches are frozen by t500 (median
freeze 2076) and the deep pump (D ~ 6) is the field's losing economy (pumps 19% against HammerSpb, Aegis
0/11 against Sprint, 85-92% of pump cell-ticks spent feeding). Drop Dogma; D belongs in 12-20.

G2 [missed] Sprint loses to HammerSpb on the refill race, not on bite order: 99239 Sprint 168,555 bites,
13,853 kills, ~150 refills, 0 squares; AtomPush 16,601 refills with 5-7-energy children behind a split
path <= 20. The post lock's 5-instruction refill is the kernel's main feature and goes into every slot.

G3 [design] Front path: post lock at 5 everywhere; drop the checked lock and pre-arming (one 2-energy bite
per contact, no refill); keep blind 3 only as a rival model. A flat 5 or 4 without memory is impossible
(three instructions for the mask, one dispatch, one `mov`, one `ret`).

G4 [missed] The unexplained +1 and +3 are REST, which the replay does not log: event-free +1 share is 3%
in fat fields and 55-67% in pump fields, receiver +3 = feed 2 + rest 1, mid-tick 52-56 is capped at Tidy.
No bonus or passive gain exists; income = cells below 50 that rest; 66% of all bites (94% of Sprint's) hit
a capped eater and yield nothing.

G5 [design] Feeding rules follow from G4: capped donors (>= 47) feed the poorest neighbour at margin >= 2
so producers stay below 50; never feed a target >= 47 (Aegis wastes 34% of its feeds on full cells);
locked cells fed first so refills come from >= 16; D in {12, 16}.

G6 [decision-wrong] "The lock is mandatory because rivals bite in <= 5" overstates one match: every rival is
4 in one direction only; Sprint's 6 already wins two directions and ties one; a 5 turns the tie into a win
and never touches the 4. Rewrite designs.md item 2 and 2.1 accordingly.

G7 [design] Trio: Scourge (conversion: post lock, refill, fat-ish D = 16, no scouts), Contagion (grab: mover
front plus assist G = 8, S <= 2 from edge starts, D = 12, same kernel), Avarice/Sprint unchanged until both
have >= 50 games; then its slot becomes the D-variant of the better one, named Doctrine.

G8 [missed] The grab is undervalued: t200 leader wins 22/36, t500 leader 28/36; HammerSpb/Noob+/Aegis reach
300-440 at t50 and 1300-2300 at t200 against Sprint's ~245 and ~1200; zergling reaches 1857 at t100 by
moving. Contact comes at tick ~37 (closest pair 18 squares, 0.24 squares/tick per front).

G9 [design] Scouts S = 4 is a corner-board artefact: with contact at tick ~37 a scout walks into the
neighbour. S <= 2, only from starts within 10 of an edge, along the longest free axis; the grab tools are
movers and assist.

G10 [missed] Refill child size predicts duels: pumps 2-3 (one bite), HammerSpb 6-7 (prey rule ~12-14),
Sprint 8 (16/17) and 25 (50). Keep child >= 8 near enemies; the post-lock refill from a 50 gives 25 and
makes both halves productive eaters.

G11 [missed] Direction luck is worth ~16 points (fast side wins 19 of 29 strong pairs); our 5 removes it in
three directions, so judge the kernel on >= 50 games.

G12 [design] Keep the slow-path split under ~15 instructions and ahead of feeding: Sprint's post-t500 gains
(+2987, +2528, +2103) were dead-colony squares won by a 19-instruction split against rivals at 10-21.

G13 [experiment] Refill race: post lock 5 unguarded vs guarded 6 vs checked lock against a fat feeder with
a <= 20 split path and 6-7 children; squares per 100 ticks after the first kill and share of refills from
e < 10.

G14 [experiment] Feeding depth D in {8, 12, 16, 20} with and without locked-first against fat feeder, pump
and flat-6 non-feeder; deaths per bite received and land at t500/t3000.

G15 [experiment] Grab: mover front, assist G in {8, 12}, scouts S in {0, 2} on the measured start
distribution; targets 300-400 / 700-1400 / 1300-2300 at t50/t100/t200.

G16 [experiment] Counter-moves: blind-3 rival and a static rival with a 4-instruction refill in its fast
direction; what the 5/5 kernel loses and whether a blind-3 variant of ours gets it back.

G17 [missed] Harvesting: a second-row cell eating its own capped front cell gains +1/tick per contact cell
over resting and keeps the front's bites counting; an experiment (and a "Famine" slot only if it pays),
not a kernel rule.

G18 [design] Further data: no new replay downloads; re-run analyze.js offline on the 35 stored replays for
who takes dead squares and when (rival split-path speed) and per-colony rest counts (income); the first
kernel cell is the 4-vs-5 probe (0% vs ~50% bite-first in a rival's fast direction); watch the
leaderboard for version changes before fetching anything large.

G19 [design] Risks to carry: stun-memory persistence (detectable from our first replay: ~50% instead of
~100% in a rival's 6-direction), unguarded refills from e < 10, newborns bitten in their birth tick, feeding
from <= 2 kills the feeder, feeds into 48+ destroyed at Tidy.

G20 [decision-wrong] designs.md 1.2/1.3 need the pull-2 facts: AtomPush R 4 / L 6 / U-D >= 8 (not "<6 on
85%"), HammerSpb feeds 6 and 18 per eat pooled (4-300 by match), starts median 10 from the edge and 18
between the closest pair, split floor/ceil, cap 50 at Tidy; 1.3.4 and 1.3.5 are closed.
