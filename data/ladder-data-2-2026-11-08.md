# CellHack2 ladder data, pull 2, 2026-11-08 (for review)

Read-only pull through the logged-in site with Claude in Chrome. Extends `data/ladder-data-2026-11-08.md`
(called "pull 1") and `data/site-observations-2026-11-08.md`. Collected: leaderboard (active + retired), 16 match-list
pages (593 finished ladder matches, ids 98830-99422, listed in `data/pull2/matches-98830-99422.json`), 165 small match
pages, and **36 replays** (35 raw `.chr2.gz` kept; the raw file of 98797 was deleted to stay under the size cap, its
keyframes and summary are kept). Replays were decoded and analysed in the page with the site's `CellHackViewer.decode`;
the analyzer is `tools/pull2/analyze.js`, the aggregation is `tools/pull2/report.py`, `lists.py`, `late.py`, `sec8.py`.
Replay pace was 17 s and later 8 s between fetches (the user allowed faster); no HTTP errors, no 429, no 5xx.
Current pacing (2026-11-08): see "Pacing rules for the site" in `architecture/data-pulls.md`.
The analyzer's start-of-tick state matched the file's keyframes in every replay (kfMismatch = 0 in all 36), so the
per-tick `energies` mapping (order of cells = keyframe order, births appended, deaths removed, values at the END of
the tick) is reliable.

Conventions: UP = target y < eater y (y grows downward on the board). Energies are raw replay units. "% first" is
defined in section 3.

## 1. Headline findings

1. **Pull 1's "land is decided by tick 300-500" does not hold for many matches.** Only 2 of 36 replays have every
   colony within 5% of its final population from tick 500 on (freeze tick: min 314, median 2076, max 2999). Colonies
   that survive keep eating long after tick 500, and the winner often needs thousands of ticks to finish: Sprint went
   1108 -> 4095 after t500 in 98879, 1567 -> 4095 in 99211, 1992 -> 4095 in 99021; Brawler v2 1611 -> 3961 in 98766;
   Noob++ 1839 -> 190 in 98862; Aegis 1497 -> 0 in 99413. (Pull 1 looked at 10 matches that mostly were frozen; this
   sample is larger and includes Sprint's own matches.) Front speed and feeding after t500 matter.
2. **Sprint (flat 6, no feeding) is much better than pull 1 suggested: 52 wins in 116 games (45%) in the new
   593-match sample; leaderboard rating 1243, rank 6 of 21 active, 58 wins / 130 games.** It wins by eating rivals
   whose contact falls in their slow directions and loses to HammerSpb's cells: Sprint vs AtomPush 1/13, vs AtomCrasher
   3/10 (wins/losses in matches where both played). Sprint beats Aegis 11/0, Bulwark 11/0, Noob 9/1, squirtle 14/0,
   Noob++ 12/5, Noob+ 8/5, rooby 9/6, Brawler 6/6, Brawler v2 6/9, Bouncer 4/9.
3. **Direction profiles are stable across replays and match pull 1: every strong rival has exactly one fast
   direction (<= 5), some a second at about 6 (50-65%), and the rest >= 7.** New cells profiled: Aegis (UP only
   fast), Bouncer (DOWN fast, RIGHT = 6), Noob+ and Noob++ (DOWN only fast), zergling (UP about 6, rest slow).
   No rival changed its order between matches (cell versions on the leaderboard are unchanged since pull 1).
   Table in section 3.
4. **HammerSpb is still on top (AtomCrasher 77% wins over 195 games in both pulls, AtomPush 73%), but their
   upsets are 38 of 203 matches (19%) and come from the "pump" cells** (Bouncer 7, Aegis 7, Brawler 7, Brawler v2 6,
   Sprint 4, Noob+ 3, rooby 2, Noob++ 1, gemAlert_v4 1). Pump winners in the replays: Brawler v2 (feeds/eat 80,
   interior energy 9), Aegis (feeds/eat 37, interior 18), Brawler (feeds/eat 113 in 98911). The two HammerSpb cells
   are NOT alike: AtomCrasher feeds 1-29 per eat (pooled 6) with a fat interior (47); AtomPush feeds 4-300 per eat depending on
   the match (pooled 18). In HammerSpb vs HammerSpb matches the winner is decided by contact direction: in 99388
   AtomCrasher bit first 97% (its RIGHT front vs AtomPush), in 99324 the order was 51/54 and AtomCrasher won on land.
5. **Rule findings (section 6):** a split gives the child floor(e/2) and the parent the rest (99.5% of odd cases,
   no energy lost); an eat moves 2 energy from target to eater (1 if the target has 1); a feed always moves 2 from
   feeder to receiver, but the receiver typically ends +3 (unexplained, flagged); every colony starts with ONE cell
   at energy 10; starts are random squares, median 10 squares from the nearest edge, closest pair of starts has a
   median Manhattan distance of 18 (minimum 8).

## 2. Win rates and head-to-heads (pull 1's 398 + the new 593; all = 991 matches)

Baseline (pull 1) counts are from its section 2. Cell names have no version on the match list, versions as on the
leaderboard: AtomCrasher v7, AtomPush v5, rooby v5, Aegis v18, Noob++ v2, Noob+ v3, Bulwark v5, zergling v44,
gemAlert_v4 / v3, choochoo v2 (all unchanged).

| Cell | new wins/games | pull 1 | all | win % |
|---|---|---|---|---|
| AtomCrasher | 89/112 | 62/83 | 151/195 | 77.4 |
| AtomPush | 76/109 | 61/79 | 137/188 | 72.9 |
| Bouncer | 64/108 | 43/82 | 107/190 | 56.3 |
| Brawler v2 | 54/104 | 40/77 | 94/181 | 51.9 |
| **Sprint** | **52/116** | 12/24 | **64/140** | **45.7** |
| rooby | 42/107 | 37/71 | 79/178 | 44.4 |
| Brawler | 51/114 | 31/75 | 82/189 | 43.4 |
| Noob+ | 36/111 | 33/76 | 69/187 | 36.9 |
| Noob++ | 39/109 | 18/72 | 57/181 | 31.5 |
| Aegis | 28/112 | 27/73 | 55/185 | 29.7 |
| Noob | 27/117 | 16/83 | 43/200 | 21.5 |
| Hunter | 12/114 | 7/79 | 19/193 | 9.8 |
| gemAlert_v4 | 10/108 | 8/75 | 18/183 | 9.8 |
| squirtle | 7/120 | 4/80 | 11/200 | 5.5 |
| gemAlert_v3 / zergling | 3/116, 3/118 | 1/81, 1/81 | 4/197, 4/199 | 2.0 |
| Medic | 0/117 | 1/83 | 1/200 | 0.5 |
| choochoo, Random, Walker, Bulwark | 0 | 0 | 0 | 0 |

Leaderboard 2026-11-08 02:07 UTC (21 active cells, no new active cell since pull 1; 135 rows with retired):
AtomCrasher v7 1584, AtomPush v5 1553, Bouncer 1429, rooby v5 1339, Brawler v2 1260, **Sprint 1243 (130 games, 58
wins, avg place 1.71)**, Brawler 1227, Noob++ v2 1188, Noob+ v3 1174, Aegis v18 1172, Noob 932, Bulwark v5 858,
gemAlert_v4 820, gemAlert_v3 761, zergling v44 753, Hunter 719, squirtle 568, Random 479, Walker 426, Medic 370,
choochoo v2 -18. Retired rows with many games: Noob+ v1/v2, Noob++ v1, AtomVirus v3, AtomCrasher v2, AtomPush v3,
zergling v27/v35, Aegis v9 (history, not active). Retired but high rated: HungryHungryHippo v4 1566 (151 games),
zergling v37 1550 (25 games), AtomCrasher AI v0 1424 (44 games): none is on the ladder now.

Head-to-head, new 593 matches only (a wins / b wins / third colony won), pairs of interest:
AtomCrasher vs AtomPush 11/6/1 (n18); AtomCrasher vs Brawler 16/2/4; AtomCrasher vs rooby
16/1/3; vs Noob+ 11/2/2; vs Brawler v2 9/3/2; Aegis vs AtomCrasher 4/9/1 (AtomCrasher wins 9); AtomPush vs Aegis 13/3/6 (AtomPush wins 13); AtomPush vs Bouncer 8/6/3; AtomPush vs Brawler 7/5/5; AtomPush vs Brawler v2 8/3/4;
AtomPush vs rooby 12/1/2; Bouncer vs Aegis 15/2/4; Bouncer vs Brawler 5/8/2 (Brawler wins 8); Bouncer vs Brawler v2
5/7/2; Bouncer vs rooby 4/8/1; Brawler v2 vs rooby 11/4/7; Brawler vs rooby 7/8/3; Noob+ vs rooby 0/12/8;
Noob++ vs rooby 1/9/9; Noob vs rooby 0/13/8; Aegis vs Brawler 2/8/4; Aegis vs Brawler v2 3/7/9; Aegis vs rooby
(pull 1: 1/9/6). Sprint vs AtomPush 1/13/2, Sprint vs AtomCrasher 3/10/0 (see section 1 for the others); full table of all pairs: `data/pull2/winrates.json`. HammerSpb lost 38 of the 203
new matches that contained at least one of the two.

## 3. Direction profile with Sprint as yardstick (36 replays, 17 of them with Sprint)

Method (a variant of pull 1's, stated exactly): for each tick, for each eat by colony A in direction d, and every
other colony B that has at least one eat in the same tick: **pre** = the eat comes before ALL of B's eats of that
tick; **post** = after ALL; **mix** = in between, counted as first (1) if fewer B eats came before it than after, 0.5
if equal. "% first" = (pre + mixFirst) / n. Sprint bites in exactly 6 in every direction, so 100% = <= 5, about
50-65% = 6, 0% = >= 7. n = number of A's eats in that direction in ticks where Sprint also ate (eats counted once
per other colony B). Pooled over all Sprint replays; per-replay values are in `tools/pull2/report.py dir` output.

| Rival | UP | RIGHT | DOWN | LEFT | Reading (cost) |
|---|---|---|---|---|---|
| Aegis | 100% n126671 | 0% n14662 | 0% n115299 | 0% n38773 | U 4, others >= 8 |
| Bouncer | 0% n7706 | 48% n118885 | 100% n17701 | 0% n35980 | D 4, R 6, U/L >= 8 |
| Noob++ | 0% n70 | 0% n23147 | 100% n74489 | 0% n43707 | D 4, rest >= 8 |
| AtomCrasher | 0% n7301 | 100% n15785 | 0% n9809 | 54% n85670 | R 4, L 6, U/D >= 8 |
| AtomPush | 0% n9012 | 100% n17625 | 0% n2785 | 59% n45752 | R 4, L 6, U/D >= 8 |
| Brawler v2 | 100% n27894 | 0% n27279 | 0% n4970 | 51% n5809 | U 4, L 6, R/D >= 8 |
| Brawler | 100% n21701 | 0% n8508 | 0% n15580 | 54% n17198 | U 4, L 6, R/D >= 8 |
| rooby | 100% n312 | 66% n25035 | 0% n26453 | 0% n2271 | U 4, R 6 (a bit slower), D/L >= 8 |
| Noob+ | 0% n4038 | 0% n5034 | 100% n26092 | 0% n13354 | D 4, rest >= 8 |
| zergling | 33% n11004 | 0% n5947 | 0% n3893 | 0% n3764 | U 6, rest >= 8 |
| Bulwark | - | 100% n77 | 100% n6714 | 100% n7116 | R/D/L <= 5 (small n; bites rarely) |
| gemAlert_v4 | 0% n1268 | 0% n4731 | 0% n1341 | 0% n4339 | all >= 8 |
| squirtle | 0% n3369 | 0% n3978 | 0% n281 | 0% n1187 | all >= 8 |
| gemAlert_v3 | 0% n24 | 0% n504 | 0% n222 | 0% n4206 | all >= 8 |
| Random | 0% n448 | 0% n428 | 0% n383 | 0% n467 | all >= 8 |

Goal check: all four directions with n >= 200 for Bouncer, Aegis, Noob+, Noob++ (UP only n70; the UP cell was never
reached), rooby (UP n312, LEFT n2271 now enough), AtomPush, AtomCrasher (UP, DOWN now n >= 7301 / 9809), Brawler,
Brawler v2 (DOWN n4970), zergling, gemAlert_v4. Missing: Noob++ UP (n70), Bulwark UP (no contact). The cost
numbers 4 / 6 / >= 8 are inferred from the order only (pull 1's inference method); the order relation of the
strong cells to each other agrees: e.g. Brawler v2 UP bit first 76-90% vs AtomPush UP in 98854 / 99304, Aegis UP 91%
(99304) and 74% (99208) vs AtomPush.
Orders did not change between matches (per-replay values, e.g. Brawler LEFT 49-73%, Bouncer RIGHT 47-71%, AtomCrasher
LEFT 51-68%, AtomPush LEFT 53-60%). A "6" reading is a tie, so the exact 6 vs 5 can only be told by a probe.

## 4. Rival fingerprints (all replays, all pooled per cell)

Split threshold = most common parent energy just before a split (the parent energy at the end of the previous tick;
before = child + after held in 99.7% of attributed splits, so no passive gain was missed). "feeds/eat" = feeds divided
by eats of enemies, pooled. front / interior = mean cell energy of cells with an enemy orthogonally adjacent vs the
rest at keyframes 500 / 1000 (means across replays). insns = from the match page.

- **AtomCrasher** (16 replays): no moves. Split energies are spread out (5: 21%, 12: 9%, cap 50: 9%, 8: 7%): not a
  fixed threshold. feeds/eat 6.2, fat colony: front 31.0, interior 47.5 (t500); 29.4 / 47.1 (t1000). insns 31-35 (47).
  Fast in RIGHT, 6 in LEFT. Wins on economy and grab (peak pop at t200 is about 1100-1800).
- **AtomPush** (17): no moves. Splits spread out (5: 14%, 14: 10%, 13: 10%). feeds/eat 17.8 pooled, but 4 to 300 in
  single matches (99388: 294; 99324: 4.1; 99122: 6.7; 98854: 54). front 22.0 / interior 46.0 (t500). insns 32-35 (47).
  Fast RIGHT, 6 in LEFT.
- **Brawler v2** (8): split at 5 (61%). feeds/eat 49.5 pooled (80-112 in the upset replays). Pump: front 31.5 /
  interior 11.1 (t500), 38.1 / 10.7 (t1000). insns 20-21 (23-24). Fast UP, 6 in LEFT.
- **Brawler** (7): split at 6 (69%). feeds/eat 47.6. front 19.1 / interior 13.3 (t500), 26.7 / 13.1 (t1000). insns
  20-23 (24). Fast UP, 6 in LEFT.
- **Bouncer** (7): split at 6 (63%). feeds/eat 58.8. Pump: front 28.5 / interior 9.4 (t500), 27.7 / 13.0 (t1000).
  insns 19-23 (24). Fast DOWN, 6 in RIGHT.
- **Aegis** (8): split at 5 (36%) or 7 (17%) or at cap 50 (11%). feeds/eat 31.4. front 35.1 / interior 18.9 (t500),
  31.9 / 20.1 (t1000). insns 32-35 (47-51). Fast UP only.
- **Noob+** (6): split at 5 (43%), 6, 7. feeds/eat 31.1. front 27.5 / interior 11.5. insns 19-23 (37). Fast DOWN only.
- **Noob++** (4): split at 5 (39%), 7. feeds/eat 29.3. front 32.1 / interior 13.4 (t500), 35.3 / 18.5 (t1000).
  insns 73-90 (111). Fast DOWN only.
- **rooby** (6): split at 6 (38%) or at cap 50 (25%). **Does not feed** (0.2 feeds per eat). Fat all through: front
  32.8 / interior 49.7 (t500), 38.5 / 49.8 (t1000). insns 58-76 (101). Fast UP, 6 in RIGHT.
- **zergling** (8): moves (24099 in total), splits at 5 (86%), feeds/eat 40, thin everywhere (front 9.6, interior
  13.7), insns 18-22 (51-55). Slow in all directions (UP is 6).
- **Bulwark** (3): moves (112), almost no feeding (0.2/eat), energy 50 everywhere, insns 22-26 (53-55).
- Others: Hunter, Medic, Noob, squirtle, gemAlert_v3/v4: split at 6, no moves, no feeding (gemAlert: front 24-29,
  interior 50). Walker (11166 moves), Random and choochoo move.
- **Sprint** (17 replays, for reference): splits at 5 / 16 / 17 / cap 50, interior 49.1-49.7, front 30.3 (t500) and
  34.4 (t1000), no feeding.

## 5. Start positions (keyframe 0, 36 replays; 144 colonies)

Every colony starts with ONE cell at energy 10 in all 144 cases.
```
98766: gemAlert_v4 (12,16); Brawler (37,26); Brawler v2 (61,38); AtomPush (54,25)
98790: AtomCrasher (61,18); choochoo (58,46); Aegis (46,53); rooby (53,11)
98797: Noob (21,33); zergling (5,52); AtomCrasher (49,46); Bouncer (18,18)
98843: Noob+ (24,23); Noob (53,40); AtomCrasher (51,59); zergling (17,8)
98844: Sprint (34,52); Walker (39,10); Brawler v2 (60,10); Aegis (55,14)
98854: Noob (62,33); Brawler v2 (37,45); AtomPush (61,19); Hunter (21,31)
98862: AtomPush (29,49); Noob++ (32,23); rooby (52,36); Noob+ (29,57)
98879: Sprint (22,47); Noob+ (8,33); choochoo (13,36); rooby (15,23)
98911: Brawler (24,29); gemAlert_v3 (1,22); choochoo (20,46); AtomCrasher (1,1)
98964: Noob+ (36,42); Brawler (27,11); Sprint (33,6); Aegis (14,51)
98983: Bulwark (36,17); Sprint (8,62); AtomPush (52,62); Aegis (57,21)
98989: AtomCrasher (35,13); AtomPush (6,41); Random (4,13); Brawler v2 (35,59)
99021: Random (26,43); Noob++ (58,25); gemAlert_v4 (30,28); Sprint (12,33)
99061: Brawler (48,31); zergling (51,61); AtomCrasher (61,28); Sprint (42,57)
99074: gemAlert_v3 (55,31); squirtle (34,44); Bouncer (5,44); Sprint (37,9)
99082: AtomCrasher (44,14); rooby (44,44); Brawler (12,24); Brawler v2 (62,34)
99097: Sprint (16,38); Bulwark (41,9); choochoo (9,51); Bouncer (62,26)
99109: gemAlert_v4 (11,51); choochoo (36,15); Sprint (16,32); zergling (61,4)
99119: Medic (5,30); AtomCrasher (31,20); Walker (25,2); AtomPush (47,18)
99122: AtomPush (17,55); AtomCrasher (57,22); Hunter (28,54); rooby (48,6)
99134: Noob+ (57,57); Sprint (32,19); AtomPush (29,57); Medic (22,50)
99168: Bouncer (60,62); AtomCrasher (9,35); AtomPush (46,3); Noob (35,30)
99198: Sprint (13,16); Walker (9,43); Bouncer (55,56); squirtle (43,14)
99208: zergling (17,10); squirtle (34,49); Aegis (41,56); AtomPush (50,4)
99211: Brawler v2 (4,31); Bouncer (35,43); Sprint (20,29); gemAlert_v3 (17,36)
99230: AtomPush (47,57); zergling (37,55); Bouncer (21,28); Walker (31,49)
99239: AtomPush (28,26); squirtle (7,38); Sprint (30,49); Aegis (57,27)
99273: Brawler v2 (43,2); Bulwark (25,12); Brawler (34,45); Sprint (34,57)
99291: gemAlert_v4 (30,5); zergling (3,53); Brawler (44,15); Sprint (51,54)
99304: Walker (10,37); Aegis (33,33); AtomPush (55,3); Brawler v2 (19,34)
99324: choochoo (54,53); AtomPush (45,48); AtomCrasher (35,30); Noob (34,23)
99365: Walker (20,34); Noob (38,35); AtomPush (54,9); AtomCrasher (43,25)
99371: Noob++ (44,57); AtomCrasher (52,9); AtomPush (42,25); rooby (18,7)
99388: Hunter (36,60); AtomPush (38,44); Walker (39,12); AtomCrasher (5,38)
99413: zergling (43,15); Aegis (51,49); AtomCrasher (10,1); Sprint (4,62)
99420: Noob++ (15,20); Noob+ (53,27); AtomCrasher (26,58); Sprint (56,7)
```
Distribution (arena 64x64, so the largest possible nearest-edge distance is 31):
- Nearest-edge distance (n = 144): min 1, median 10, max 30. Histogram: 0-4: 28, 5-9: 43, 10-14: 29, 15-19: 22,
  20-24: 15, 25-29: 6, 30-34: 1. 71 of 144 (49%) start within 9 squares of an edge; one start sits on square (1,1) (98911);
  a uniform random square would put 29% within 4 of an edge and 53% within 9, so the observed 19% / 49% are
  slightly below that.
- Minimum Manhattan distance between any two starts in a match (n = 36): min 8, median 18, max 42. Histogram: 0-9: 4,
  10-19: 17, 20-29: 11, 30-39: 3, 40-49: 1. Four of 36 matches have two starts within 9 squares (Manhattan) of each other.
- No evidence of structure (corners, symmetry): the starts look random over the board, with a mild bias away from
  the very edge (see above). A start margin of 1 is possible.

## 6. Rule findings

- **Split rounding (odd energy):** child gets floor(e/2), parent keeps ceil(e/2); no energy is lost.
  (5 -> 2 + 3, 7 -> 3 + 4, 13 -> 6 + 7, 17 -> 8 + 9); 143377 odd cases agree, 710 do not; even energies halve
  exactly (188172 vs 385). `before = child + after` in all but 1095 of about 332000 attributed splits. Most
  common splits: (6,3,3) 71851, (5,2,3) 69344, (50,25,25) 33945, (16,8,8), (12,6,6).
- **Eat:** moves 2 energy from target to eater (amount histogram: 2 -> 6355236 eats, 1 -> 205069). In single-event
  cases the target ends -2 (1.65 M), the eater +2 (1.48 M cases), +0 when the eater is full (2.93 M cases) or +1
  (93 k). A target dies at 0 (eats are not kills: a death event follows later).
- **Feed:** amount is always 2 (120 M feeds). The feeder ends -2 in all 25.7 M single-event cases. **The receiver
  typically ends +3 (6.38 M cases), +2 in 228 k, +0 when full (2.1 M), small negatives when it is also hit.** So a
  fed cell gains one more than the feeder pays, or fed cells also get the passive +1 below; unexplained, not guessed.
- **Passive gain (unexplained):** 17.25 M of 216 M cell-ticks with no event on the cell end the tick +1 (8%).
  It is not periodic (tick mod 12 is flat), shows at every energy level and slightly more at e < 5; the cause
  (terrain? only when below some level? random?) was not found. Idle cells with no events are otherwise
  unchanged (delta 0 in 199.5 M cases). The simulator should not assume a global per-tick income of +1.
- **Cap:** many interior means are 49.7-50.0 and splits at exactly 50 are common ((50,25,25) 33945), so cells fill
  to about 50; the running model saw receiver energies up to 54-56, so the cap may be higher or the receiver
  value includes the +3 effect. Not settled.
- **Event order:** within a tick events are in turn order and, across colonies, in order of instruction cost (a
  4-instruction colony's eats precede a 6-instruction colony's every time in the table above). Holds in every replay.
- **Diagonal eats:** 0 in all replays (the analyzer counted them): bites go only to the 4 orthogonal neighbours.
- **Start state:** one cell per colony, energy 10, random square (section 5).
- **Contradictions with the docs:** the starts are not corners; nothing else contradicts the docs read so far (the
  split rule and the eat/feed amounts are not in the docs I have).
- **Early end:** a match ends at "last colony standing" when everyone else is dead (reason 2): 14 of 36 replays;
  the other 22 ran to the 3000-tick limit (reason 1).

## 7. Simulator validation table

Per replay and colony: population at ticks 50 / 100 / 200 / 500 / 1000 / end, mean energy at ticks 200 and 1000
(keyframes), feeds per eat, freeze tick of the match. 36 replays x 4 colonies = 144 rows, so the full table is in
`data/pull2/validation-table.md` (generated by `tools/pull2/report.py val`). Short extract (the rows most useful for
calibrating the sim):

| match | colony | t50 | t100 | t200 | t500 | t1000 | end | E t200 | E t1000 | f/eat | freeze |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 98854 | Brawler v2 | 350 | 1391 | 2530 | 2860 | 3234 | 4095 | 9.2 | 11.1 | 80 | 2938 |
| 98854 | AtomPush | 238 | 774 | 1321 | 1234 | 860 | 0 | 37.0 | 45.1 | 54 | 2938 |
| 99122 | AtomPush | 349 | 1014 | 2087 | 2468 | 2764 | 3651 | 43.6 | 47.7 | 6.7 | 2999 |
| 99122 | AtomCrasher | 283 | 756 | 1152 | 1169 | 1178 | 368 | 41.5 | 42.2 | 28.8 | 2999 |
| 99324 | AtomCrasher | 255 | 789 | 1837 | 2999 | 3268 | 3642 | 39.9 | 49.6 | 2.8 | 2226 |
| 99324 | AtomPush | 403 | 1024 | 1325 | 1096 | 827 | 453 | 43.6 | 46.2 | 4.1 | 2226 |
| 99304 | Brawler v2 | 325 | 1055 | 2007 | 2852 | 3706 | 4095 | 9.7 | 11.9 | 83 | 2076 |
| 99304 | AtomPush | 260 | 692 | 771 | 626 | 390 | 0 | 38.5 | 42.6 | 99 | 2076 |
| 99208 | Aegis | 372 | 1198 | 2396 | 2839 | 2959 | 3257 | 18.0 | 21.8 | 37 | 2405 |
| 99208 | AtomPush | 312 | 615 | 922 | 1248 | 1132 | 838 | 38.1 | 40.6 | 214 | 2405 |
| 98911 | Brawler | 269 | 1134 | 2800 | 3652 | 3652 | 3653 | 9.3 | 9.2 | 113 | 329 |
| 98911 | AtomCrasher | 131 | 345 | 414 | 444 | 444 | 443 | 46.4 | 49.0 | 1.6 | 329 |

Readings: peak growth early is 250-400 at t50, 700-1400 at t100, in all cells (the corner-start sim should be about
4x slower than this). Pump cells (Brawler v2, Bouncer, Brawler, Aegis) keep interior energy at 9-20 and beat fat
economies by being more numerous (2000-2500 by t200) rather than by energy.

## 8. The matches chosen and why (one line each; 36 replays)

Purpose a = Sprint yardstick (17), b = HammerSpb at its best (6), c = upsets of HammerSpb (6), d = contested /
late-moving candidates (4), f = pull-1 re-downloads (3). Placement and final population in brackets. (e: no new
cells appeared, so none; of the pull 1 re-download list only 98766, 98790 and 98797 fitted into the size cap.)

- **a (17):** 99211, 99198, 99109, 99021, 98879, 98964, 99273, 99291, 99097, 99074, 99061, 99413, 99420, 99134,
  99239, 98983, 98844: chosen from the 116 Sprint matches (match pages fetched) because Sprint survived long and
  the rivals needed were beside it. Sprint won 15 of the 17 (it lost 99134 and 99239 to AtomPush).
- **b (6):** 99324 (AtomCrasher 3642, AtomPush 453), 99119 (AtomCrasher 2871, AtomPush 1225), 99168 (AtomCrasher
  2718, AtomPush 1370), 99388 (AtomPush 2067, AtomCrasher 2029), 99122 (AtomPush 3651, AtomCrasher 368), 99371
  (AtomPush 3107, AtomCrasher 573): large margins and both together.
- **c (6):** 98854 and 99304 (Brawler v2 4095, AtomPush 0), 99230 (Bouncer 4095, AtomPush 0), 99208 (Aegis 3257,
  AtomPush 838), 98843 (Noob+ 4095, AtomCrasher 0), 98911 (Brawler 3653, AtomCrasher 443).
- **d (4):** 98989 (AtomCrasher/AtomPush/Brawler v2 1656/1402/1035), 99082 (rooby 1847, Brawler 1252, AtomCrasher
  546, Brawler v2 444), 99365 (AtomCrasher 2148, AtomPush 1942, peak 2916), 98862 (rooby 2002, AtomPush 1892, Noob++
  190, peak 1925). Late movement was found, as the replays show: Noob++ lost 1649 squares after t500 in 98862.
  Largest post-t500 changes among all replays: 98879 Sprint +2987, 99211 Sprint +2528, 98766 Brawler v2 +2350,
  99021 Sprint +2103, 98862 Noob++ -1649, 98964 Sprint +1624, 99413 Aegis -1497, 99097 Sprint +1459, 99420 Noob++
  -1430.
- **f (3):** 98766, 98790, 98797 (re-downloads). 98797's raw file was deleted because it alone was 53 MB; its keyframes
  and summary exist.

All 36 with placement and final populations:
- 98766 (3000 ticks): 1.Brawler v2 3961, 2.AtomPush 134, 3.Brawler 0, 4.gemAlert_v4 0
- 98790 (2557, last colony): 1.Aegis 4095, 2.rooby 0, 3.AtomCrasher 0, 4.choochoo 0
- 98797 (3000): 1.Bouncer 4080, 2.AtomCrasher 14, 3.Noob 0, 4.zergling 0
- 98843 (2417): 1.Noob+ 4095, 2.AtomCrasher 0, 3.Noob 0, 4.zergling 0
- 98844 (1167): 1.Sprint 4095, 2.Aegis 0, 3.Brawler v2 0, 4.Walker 0
- 98854 (2939): 1.Brawler v2 4095, 2.AtomPush 0, 3.Hunter 0, 4.Noob 0
- 98862 (3000): 1.rooby 2002, 2.AtomPush 1892, 3.Noob++ 190, 4.Noob+ 0
- 98879 (2517): 1.Sprint 4095, 2.rooby 0, 3.Noob+ 0, 4.choochoo 0
- 98911 (3000): 1.Brawler 3653, 2.AtomCrasher 443, 3.gemAlert_v3 0, 4.choochoo 0
- 98964 (1522): 1.Sprint 4095, 2.Aegis 0, 3.Noob+ 0, 4.Brawler 0
- 98983 (3000): 1.Sprint 1406, 2.Aegis 1343, 3.AtomPush 1334, 4.Bulwark 0
- 98989 (3000): 1.AtomCrasher 1656, 2.AtomPush 1402, 3.Brawler v2 1035, 4.Random 0
- 99021 (2254): 1.Sprint 4095, 2.Noob++ 0, 3.gemAlert_v4 0, 4.Random 0
- 99061 (3000): 1.Sprint 3114, 2.AtomCrasher 982, 3.Brawler 0, 4.zergling 0
- 99074 (3000): 1.Sprint 2514, 2.Bouncer 1581, 3.gemAlert_v3 0, 4.squirtle 0
- 99082 (3000): 1.rooby 1847, 2.Brawler 1252, 3.AtomCrasher 546, 4.Brawler v2 444
- 99097 (3000): 1.Sprint 4065, 2.Bulwark 24, 3.Bouncer 0, 4.choochoo 0
- 99109 (1120): 1.Sprint 4095, 2.gemAlert_v4 0, 3.zergling 0, 4.choochoo 0
- 99119 (3000): 1.AtomCrasher 2871, 2.AtomPush 1225, 3.Medic 0, 4.Walker 0
- 99122 (3000): 1.AtomPush 3651, 2.AtomCrasher 368, 3.rooby 69, 4.Hunter 0
- 99134 (3000): 1.AtomPush 2169, 2.Sprint 1920, 3.Noob+ 0, 4.Medic 0
- 99168 (3000): 1.AtomCrasher 2718, 2.AtomPush 1370, 3.Bouncer 0, 4.Noob 0
- 99198 (891): 1.Sprint 4095, 2.Bouncer 0, 3.Walker 0, 4.squirtle 0
- 99208 (3000): 1.Aegis 3257, 2.AtomPush 838, 3.zergling 0, 4.squirtle 0
- 99211 (2047): 1.Sprint 4095, 2.Brawler v2 0, 3.Bouncer 0, 4.gemAlert_v3 0
- 99230 (1830): 1.Bouncer 4095, 2.AtomPush 0, 3.zergling 0, 4.Walker 0
- 99239 (3000): 1.AtomPush 2749, 2.Sprint 1344, 3.Aegis 0, 4.squirtle 0
- 99273 (809): 1.Sprint 4095, 2.Brawler 0, 3.Bulwark 0, 4.Brawler v2 0
- 99291 (844): 1.Sprint 4095, 2.Brawler 0, 3.gemAlert_v4 0, 4.zergling 0
- 99304 (2077): 1.Brawler v2 4095, 2.AtomPush 0, 3.Aegis 0, 4.Walker 0
- 99324 (3000): 1.AtomCrasher 3642, 2.AtomPush 453, 3.Noob 0, 4.choochoo 0
- 99365 (3000): 1.AtomCrasher 2148, 2.AtomPush 1942, 3.Noob 0, 4.Walker 0
- 99371 (3000): 1.AtomPush 3107, 2.AtomCrasher 573, 3.rooby 406, 4.Noob++ 0
- 99388 (3000): 1.AtomPush 2067, 2.AtomCrasher 2029, 3.Walker 0, 4.Hunter 0
- 99413 (3000): 1.Sprint 2432, 2.AtomCrasher 1664, 3.Aegis 0, 4.zergling 0
- 99420 (3000): 1.Sprint 2423, 2.AtomCrasher 1672, 3.Noob++ 0, 4.Noob+ 0

Could not get / limits:
- Per-match place / final pop / insns were fetched only for 165 matches (the 116 Sprint matches and 49 HammerSpb
  matches chosen); for the other 593-165 list matches only the colonies and the winner are known.
- The list shows cell names without version or player; the leaderboard shows the same versions as pull 1.
- No new cells, so no replays for purpose e. Of pull 1's 11 re-download candidates only 3 were taken (size cap).
- The replay size was larger than planned: later replays (3000-tick matches) are 25-53 MB gzipped each, so 650 MB
  held 36 replays rather than 45.
- Parent attribution of splits is by "the only same-colony orthogonal neighbour with no event whose energy fell",
  so 10-30% of births are ambiguous and skipped (counts in each summary). Feeder / receiver energy "before" are the
  running values from the end of the previous tick plus the earlier events of the same tick; because of the
  unexplained +1 and +3 effects they can be off by 1.
- Bite-first for pairs where the other colony has no eat in the tick is not counted.
- UP / RIGHT / DOWN / LEFT are relative to the board with y growing downward; if the game's own UP means the other
  y direction, swap UP and DOWN throughout.

## 9. File index

```
data/pull2/leaderboard-2026-11-08T0207Z.json   active (21) and retired (135 rows) leaderboard snapshot
data/pull2/matches-98830-99422.json            593 finished ladder matches (colonies, winner)
data/pull2/winrates.json                       win rates, head-to-heads, HammerSpb upsets (from tools/pull2/lists.py)
data/pull2/sprint-match-pages.json             match-page rows for the 116 Sprint matches
data/pull2/other-match-pages.json              match-page rows for 49 HammerSpb / upset candidates
data/pull2/validation-table.md                 section 7, all 144 rows
data/pull2/site/viewer.js                      the page's replay viewer script (19 KB), for an offline decoder
data/pull2/summaries/<id>.json                 36 summaries (0.67 MB in total)
data/pull2/keyframes/<id>.kf.json.gz           36 files (37 MB): all keyframes as [id,c,x,y,e], header, end
data/pull2/replays/<id>.chr2.gz                35 raw replays (595 MB; git-ignored)
tools/pull2/analyze.js, lists.py, select_sprint.py, report.py, late.py, sec8.py, collect.sh
```
Total size of `data/pull2/`: 604 MB (633 MB in decimal units: 595 MB replays, 37 MB keyframes, 1 MB everything else),
under the 650 MB cap. Pull 1 data files are unchanged.

Per-summary fields (for the simulator engineer): starts with nearest-edge distance, start pair distances, population
every 10 ticks, per-colony totals (births, moves, deaths, eats of enemies / friends, feeds, eat and feed amounts),
mean energy at every keyframe and at the end, front vs interior means at keyframes 200 / 500 / 1000 / 2000, bite
first by pair and direction (`pre` / `post` / `mix` / `mixFirst` / `n`), split fingerprint (parent energy before,
child energy, parent energy after, triples), feed fingerprint (amount, feeder energy before, receiver energy before),
eat amount histogram, freeze tick, per-role energy deltas (`deltaHist`: untouched / eater / target / feeder /
receiver / several events) and the validation counters.
