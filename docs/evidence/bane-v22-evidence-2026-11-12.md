# Bane v2.2: evidence pack (2026-11-12)

> Note: paths under `data/` in this file name local working data that is not published in the repo. See [data-pulls.md](../../architecture/data-pulls.md). Other evidence files are in this folder.

Purpose: every measure the real replays and match pages give on Bane v2.2 (cell 289), stage by stage, so that a next
version can be planned that closes real gaps without giving up anything Bane already does well. Facts first;
inferences are marked **(inferred)**. No rival models and no games against them were used (user rule 2026-11-12);
the solo engine (our own cell alone on the board) is used only for the start-square potential.

Files (all in `data/evidence-2026-11-12/`, scripts in `scripts/`, run with `python -I`):

| File | What | Script |
|---|---|---|
| `review-all.csv` | per colony per game: start (x, y, wall, near), cells at t30/60/100/200/500/end, action shares per window (split, move, feed, hold, capidle, contact, bitten first, deaths, take, retake) | `tools/replay/review.py` |
| `full-front.csv` | per colony per game: front contact cell-ticks, fresh vs ongoing contact and who bit first, squares taken from freed enemy squares (child energy, dead within 5), contested empty squares won/lost by window, first contact tick per pair and who closed in, bites given/taken per pair, squares taken per pair | `scripts/front.py`, `scripts/front_many.py` |
| `eval-all.csv`, `eval-all.txt` | per game: Bane vs the deciding rival (winner if Bane lost, runner-up if Bane won) on every measure above plus the solo potential of each start square; pooled means; Spearman with Bane's share | `scripts/eval_all.py` |
| `lost-squares.csv`, `ls-summary.txt` | every contested empty square-tick (cells of two or more colonies on its edges at tick start; squares freed by a death the tick before are excluded): outcome per colony, the state of that colony's best-placed neighbour, and every fill (filler energy, alive after 10 ticks, square still held after 10 ticks) | `scripts/lost_squares.py`, `scripts/ls_sum.py` |
| `bites.csv`, `bites-summary.txt` | per colony per window: front contact, stuns suffered, bites, friendly bites, kills, bite chains, what the killer did on the next tick, who filled the freed square, bites suffered at energy <= 2 / <= 4 | `scripts/bites.py`, `scripts/bites_sum.py` |
| `budget.csv`, `budget-summary.txt` | action budget: every cell-tick by action x space (open/boxed) x enemy (front/near/far) x energy bucket | `scripts/budget.py` |
| `solo-all2.csv` | Bane v2.2 alone on the board from each start square: cells at t20..t100 (start-square potential) | `scripts/solo_baseline.py` |

Replays: `data/pull7` (2 Bane v2.2 games), `data/pull8` (12 consecutive Bane games, 129850-129954), `data/pull9`
(44: 12 consecutive Bane games 131017-131125, 6 earlier Bane losses, 7 Bane games vs the Yen cells 131188-131332,
19 Penalty games). Match list: `data/pull9/ourmatches-2026-11-12.json` (1000 games, ids 127696-131127). Match pages:
`data/pull9/matches-2026-11-12T02-21-18.json` (60 pages: placement, rating, peak, energy, instructions per turn).

## 0. Samples and labels

- The site names every Bane version "Bane". Labels by match id: v1 < 124690 (cell 272), v2.0 from 124697 (rating
  restarts at 1000 there), v2.1 (cell 287, stored bite; max instructions per turn rises 86 -> 91 between 124926 and
  126918), v2.2 (cell 289) from about 127810 (from the leaderboard game count; v2.1 and v2.2 have the same max).
- Unbiased samples: U8 = pull 8 (12 consecutive games, 10 won), U9 = 131017-131125 (12 consecutive games, 10 won).
- Extra losses LX: 129255, 129308, 130482, 130515, 130711, 130818, 130915, 130988 (every v2.2 loss replay still on
  the site at pull time; older ones had expired).
- NS (vs CogSpore-Siect-F): 131198, 131245, 131332 (all lost). 131188 also lost but Conviction was in it (excluded).
- NV (vs CogSpore - VarSi, after U9): 131265, 131276 lost, 131312 won.
- Total in the per-game tables: 38 games (21 won, 17 lost). Losses are over-sampled (LX, NS): use U8+U9 for rates.

## 1. Results (match list, single own cell, ids 127810-131127, v2.2 era)

| Cell | All | vs VarSi | vs Siect-F | vs Colossus | vs CogSpore | vs medivac | vs CogBloomXT | vs NomNom2 | vs AtomCrasher | vs Aegis |
|---|---|---|---|---|---|---|---|---|---|---|
| Bane v2.2 | 298/329 (91%) | 9/21 | 0/3 | 18/29 | 23/29 | 21/23 | 21/26 | 28/30 | 36/37 | 24/26 |
| Conviction | 251/293 (86%) | 11/17 | - | 10/26 | 16/29 | 13/19 | 23/29 | 17/19 | 23/26 | 21/22 |
| Penalty | 112/139 (81%) | 3/7 | 0/1 | 5/14 | 6/10 | 2/10 | 4/7 | 9/9 | 6/8 | 11/11 |

(Siect-F numbers include games after 131127 that were pulled on purpose; Bane's last 50 games at 2026-11-12 ~02:30
UTC: 0/4 vs Siect-F, 2/7 vs VarSi.) Leaderboard ~02:30 UTC: VarSi v2 1692, Bane 1597, Siect-F 1474 (34 games, 32 won),
Colossus 1456, medivac 1383.

## 2. Rules that decide the measures (sim/engine.py, ruleset v9)

- Turn order inside a tick: fewest executed instructions first (taken jumps and the exit count); the seed breaks ties.
- A cell bitten before its turn is stunned: it loses that turn and its memory writes are dropped.
- EAT takes min(2, target energy) and gives it to the eater; FEED gives 2; REST is the only energy income (+1).
  Energy start 10, cap 50. A split needs energy >= 5; the child gets floor(e / 2); a split into an occupied square
  does nothing. A dead cell holds its square until the end of the tick: a freed square opens on the next tick.
- So in an ongoing exchange the cell with the cheaper bite takes 2 per tick and the other never answers.

## 3. Instruction costs

Bane v2.2 paths (cells/bane2.asm header): stored bite 4 (re-checks that the bitten square still holds an enemy);
first bite 16; refill split (an empty neighbour with an enemy beside or beyond it, energy >= 12) 16; other split
(energy >= 16) 16; diagonal enemy: rest 31, hold 33; walker move 39; settled rest 33; first child forward 43; other
children 47-66; boxed block (no empty neighbour: feed) Bane's + 5.
Conviction / Penalty: bite queue 3 (shift, load, exit: blind, does not look at the square); scan bite 18-19; every
other path +3 (refill 14). Penalty's last queue entry is a split into the target's square.

Match pages, instructions per turn, median of game means (max): Bane v2.2 81 (91), Conviction 78 (89), Penalty 78
(89), CogSpore - VarSi 87 (203), CogSpore-Siect-F 87 (202), Colossus 65 (106), medivac 47 (62), CogBloomXT 51 (190),
CogSpore 45 (190). (Means are dominated by interior cells, so they say little about the front paths.)

Bite order measured in ongoing contact (an enemy beside me that was beside me last tick), all games pooled
(`full-front.csv`, share of contact cell-ticks where the cell bit first / was bitten first):

| Cell | games | fresh contact: bit first / bitten first | ongoing: bit first / bitten first |
|---|---|---|---|
| Bane v2.2 (pull 9 set, loss-heavy) | 27 | 61 / 38 | 62 / 38 |
| Bane v2.2 (pull 8, consecutive) | 12 | 86 / 12 | 89 / 11 |
| CogSpore-Siect-F | 5 | 96 / 3 | 88 / 12 |
| CogSpore - VarSi | 15 | 77 / 22 | 35 / 65 |
| Colossus | 17 | 67 / 32 | 26 / 74 |
| medivac | 6 | 62 / 37 | 44 / 56 |
| Penalty (3-insn queue) | 19 | 35 / 59 | 77 / 22 |

Per game, Bane's ongoing bit-first share vs Siect-F: 3.3, 0.9, 5.2% (131198, 131245, 131332; 131188 11.3%); vs
VarSi 44-96%; vs Colossus 99-100%. Penalty vs Siect-F (131094): 48 / 52. **Measured exactly in section 12:** Siect-F
bites in <= 3; VarSi, CogSpore, CogBloomXT bite UP / DOWN in exactly 4 and LEFT / RIGHT in 5-15; medivac and Colossus
bite in exactly 5.
The floor for any bite is 2 (load the action, exit), but a 2-instruction bite cannot advance or clear anything, so it
would repeat forever; 3 is the floor for a queue that ends.

## 4. Where the losses happen (eval-all.csv)

Lead over the deciding rival (Bane cells minus rival cells):

| | ahead at t30 | t60 | t100 | t200 | t500 | end |
|---|---|---|---|---|---|---|
| 17 losses | 13 | 3 | 2 | 2 | 1 | 0 |
| 21 wins | 20 | 20 | 20 | 20 | 17+ | 21 |

- Bane's opening is the fastest to t30 (ahead in 33 of 38 games).
- 14 of 17 losses are decided between t30 and t100; the other 3 (Siect-F) are lost late with Bane ahead at t100 in
  two of them (131245 +672, 131332 +1063 at t100; both lost).
- One comeback: 131102 (behind vs VarSi t30-t200, won).

Start squares (solo potential of our opening from each colony's square, solo-all2.csv; d = Bane minus rival at t60):

| Start | won | lost |
|---|---|---|
| bad (d < -250) | 6 (all vs mid cells: CogBloomXT, Aegis, gemAlert, Hunter, AtomCrasher, NomNom2) | 7 (VarSi 3, Colossus 2, CogSpore, CogBloomXT) + 1 Siect-F |
| equal (-250..250) | 7 | 7 (VarSi 5, CogSpore 1, Colossus 1) |
| good (d > 250) | 8 (incl. VarSi 3) | 2 (both Siect-F) |

- In bad-start losses the real t60 gap is about the start's gap (e.g. 130915: -817 expected, -652 real; 130988 -776 /
  -561; 131114 -733 / -524): Bane did what its square allowed.
- In equal-start losses Bane fell 100-320 cells further behind than the starts predict by t60 and 100-1200 by t100.
  Against VarSi on equal starts Bane is 0 / 5 (129308, 130482, 130818, 131265, 131276).
- Siect-F beat Bane from worse squares (131245 d = +315, 131332 d = +664).

## 5. Opening (t0-60)

- t30 real / solo from the own square: Bane 0.91-1.02 in pull 7-9 v2.x games; median over pulls 2-8 at t60:
  Bane v2.2 0.82, CogSpore 0.82, VarSi 0.82, medivac 0.70, Colossus 0.67. No colony beat our solo opening from its own
  square at t60 in ~700 colony-games.
- t60 real / solo follows t30-60 contact (< 1% of cell-ticks in contact: 0.88-1.00; 6-12%: 0.28-0.56).
- Bane vs VarSi on equal starts, share of cell-ticks t30-60 (review-all.csv): Bane split 4.9-6.7, move 5.4-7.2, feed
  5.2-6.2, hold 0.9-2.6; VarSi split 6.3-7.5, move 6.2-9.0, feed 0, hold 0.2-0.8. VarSi loses 2-4x more cells
  (t30-60 deaths 65-195 vs 16-104) and still grows more.
- Solo opening search (data/opening-search-2026-11-11.md): the best variant ("first child long 8/2, split toward the
  emptiest side") is ahead of v2.2 at every tick, by 2-6% (t30 143 vs 137, t60 1115 vs 1063, t100 3012 vs 2942).

## 6. First contact

First contact with the deciding rival: wins t4-92 (7 of 20 before t30), losses t18-54 (7 of 17 before t30). The
rival moved into contact (it moved or was born there on the tick before) in 16 of 20 wins and 16 of 17 losses; Bane
in 9 of each. Timing and closing alone do not separate wins from losses.

## 7. Front: bites (bites-summary.txt; windows a t<60, b 60-100, c 100-300, d 300+)

Own cells stunned per contact cell-tick: Bane v2.2 34 / 28 / 28 / 39%; VarSi 40 / 40 / 54 / 66; Colossus 39 / 53 / 61 /
67; medivac 43 / 49 / 51 / 48; Siect-F 14.5 / 9 / 8.5 / 12; Penalty 44 / 28 / 21 / 22; Conviction 35 / 24 / 17 / 16.
Mean bite chain on one target: Bane 5.8, Siect-F 9.6, Conviction 6.1, Penalty 4.7, VarSi 2.7, Colossus 2.9.

After a kill, the killer's next tick (Bane, by window; corrected 2026-11-12 with energy-matched split parents, was
take 21 / 39 / 53 / 48, none 41 / 27 / 19 / 20): take the freed square 21.8 / 38.8 / 52.4 / 49.0%, no event 38.6 / 26.6 /
16.6 / 15.4%, stunned 17.9 / 11.9 / 8.5 / 10.9%. The freed square went to Bane on the next tick 34.3 / 51.8 / 66.2 /
61.6%.
Siect-F vs Bane, 131245: Siect-F bit 190,004 times in 7,279 chains (26 ticks each); after a kill it had no event 71%
of the time and Bane refilled the freed square 79% of the time; Bane's front cells were stunned on 99% of their
contact cell-ticks.
Blind-or-checked test (`blind.csv`, scripts/blind.py): a cell that bit square S last tick, is not stunned, finds S
empty and has another enemy on a different edge. Siect-F (131245) bit the other enemy 83% of the time, no event 16%:
**not** a pure blind repeat. **(inferred)** A 3-instruction repeat bite with a queue sized to kill the target (like
Conviction's, without its minimum length), then a scan; the view has no direction-indexed array (cellhack.inc: VIEW_CELLS
is a row-major 5x5, neighbours at 7 / 13 / 17 / 11), so a checked bite in any direction needs 4 instructions; 3 is
possible checked only for one fixed direction.
Refills into squares freed by an enemy kill (131245): Bane refilled 4,931 squares freed by Siect-F kills; the killer
bit the new child on its first live tick 87% of the time, bit it 4.1 times on average (about 8 energy, the child's
mean birth energy was 8.1), and 44% of those children died within 5 ticks. **(inferred)** Against a faster biter the
refill rule feeds the rival: roughly 40,000 energy in that game.
Friendly bites: Bane 0; Penalty 0.4-1.0 per 100 enemy bites; Conviction 0.1-0.7.

## 8. Front: land (ls-summary.txt)

> **SUPERSEDED 2026-11-12.** The numbers in this section came from guessed split parents (first friendly neighbour without an event; 20-30% of splits sat at < 5 energy). The corrected data uses energy-matched parents (scripts/parents.py): ls-summary.txt and lost-squares.csv (regenerated), m1-gate-summary.txt (gate split by rule). Keep the text below only as history.

Contested empty squares, share of square-ticks won / lost (t<60 | t60-100 | t100+):

| Cell | games | t<60 | t60-100 | t100+ |
|---|---|---|---|---|
| Bane v2.2 | 39 | 9.7 / 17.1 | 13.3 / 20.7 | 19.5 / 14.9 |
| CogSpore - VarSi | 17 | 13.1 / 13.7 | 19.4 / 15.7 | 17.8 / 21.8 |
| Colossus | 24 | 25.8 / 9.8 | 30.4 / 13.9 | 28.0 / 27.2 |
| medivac | 15 | 25.2 / 10.2 | 31.0 / 13.3 | 41.1 / 17.3 |
| CogSpore-Siect-F | 5 | 13.6 / 15.7 | 22.3 / 18.0 | 8.5 / 10.5 |
| Penalty | 19 | 7.9 / 23.0 | 11.5 / 28.2 | 28.6 / 11.5 |
| Conviction | 5 | 10.7 / 13.9 | 12.9 / 21.3 | 38.9 / 17.2 |

Bane's best-placed neighbour on squares Bane lost, t<60: energy 5-11 and no event 28%, biting 28%, energy < 5 24%,
stunned 11%, split elsewhere 7%, energy >= 12 and no event (a lost race at full energy) 1%. t60-100: biting 38, 5-11
27, < 5 19, stunned 8, split 6, >= 12 1.
**(inferred)** Bane does not lose these squares on instruction count; it loses them to the refill gate (a square
with an enemy beside it is split into only at energy >= 12) and to front cells that are biting or poor.

Fills of contested squares: filler energy, alive after 10 ticks, square held by the same colony after 10 ticks
(t<60; t60-100):
- Bane: child 1-2: n 268 alive 28% held 69%; 3-4: n 134, 72%, 92%; 5-6: n 184, 73%, 86% (t60-100: 3-4 80/93, 5-6
  85/94, 7-9 92/98). Walkers with 1-2 energy: alive 20%, held 45%.
- VarSi: child 1-2: n 881, 35%, 62% (t60-100: n 1046, 39%, 73%); 3-4: n 99, 54%, 74%.
- Colossus: 1-2: n 637, 61%, 78%; 3-4: n 820, 76%, 91%.
- Siect-F: 1-2: n 274, 77%, 92%; 3-4: n 48, 77%, 85%.
- Penalty: 1-2: n 159, 23%, 52%; 3-4: 70%, 82%; walkers 1-2: 15%, 26%.
Per game the fill counts differ more than the rates: in 131276 VarSi filled 158 contested squares before t60, Bane 70.

Scale check, Bane vs VarSi (t < 100; squares Bane lost by the state of its neighbour; VarSi's and Bane's contested
wins; cell gaps at t60 / t100):

| game | result | gap t60 / t100 | Bane lost (5-11 energy, no event / biting / < 5 / stunned) | VarSi won | Bane won |
|---|---|---|---|---|---|
| 129308 | L equal start | -316 / -723 | 127 (43 / 37 / 16 / 20) | 126 | 78 |
| 130482 | L equal | +50 / -188 | 153 (62 / 48 / 21 / 10) | 236 | 112 |
| 130818 | L equal | -284 / -753 | 87 (26 / 36 / 12 / 6) | 65 | 69 |
| 131265 | L equal | -139 / -154 | 131 (39 / 43 / 27 / 9) | 143 | 97 |
| 131276 | L equal | -279 / -1048 | 354 (110 / 118 / 45 / 46) | 409 | 149 |
| 130915 | L bad start | -652 / -1515 | 78 (26 / 27 / 16 / 7) | 194 | 57 |
| 130988 | L bad | -561 / -1199 | 118 (49 / 29 / 30 / 7) | 108 | 71 |
| 131114 | L bad | -524 / -977 | 94 (18 / 35 / 20 / 6) | 58 | 33 |
| 131102 | W good | -155 / -149 | 153 (45 / 46 / 28 / 18) | 101 | 110 |
| 131312 | W good | +157 / +1268 | 182 (53 / 46 / 43 / 27) | 86 | 108 |
| 129850 | W good | +515 / +929 | 101 (28 / 32 / 17 / 13) | 102 | 91 |

**(inferred)** The squares lost to the refill gate (26-110 per game before t100) are about a tenth of the t100 gaps
(154-1048 cells) in the losses: a real gap, but not by itself the size of what decides these games, unless each early
square compounds strongly. Most cell-ticks are away from the front (85-90% "far"): there VarSi keeps more cells with an
empty edge (b: 33.9% of far cell-ticks open vs Bane 29.2%), moves more (8.1 vs 6.6) and does not feed (0 vs 5.9).

Growth t30 -> t60 in the equal-start VarSi games (cells at t60 / cells at t30): Bane 7.7, 7.0, 5.7, 9.1, 7.4;
VarSi 12.0, 6.6, 8.8, 8.6, 9.5 (129308, 130482, 130818, 131265, 131276). Squares taken from third colonies (whole
game): VarSi 12, 841, 49, 433, 75; Bane 4, 0, 73, 242, 250.

## 9. Interior and third colonies

- Feed share of cell-ticks at t30-60: Bane 4.9-8.7%; VarSi, CogSpore, Siect-F 0. At t60-100: Bane 9-23%, Colossus
  43-69% (4 games as the deciding rival), Aegis 56-64%, NomNom2 40%.
- Cells idle at the energy cap, t100-200: Bane 3-13%; VarSi 42-81%; CogSpore 72-78%; Colossus 22-35%.
- Squares taken from third colonies (freed squares of colonies other than the deciding rival): high in Bane's wins
  (took_third Spearman with share +0.76).

## 9b. Action budget (budget-summary.txt; windows a t0-30, b 30-60, c 60-100, d 100-200, e 200+)

> **SUPERSEDED 2026-11-12.** The numbers in this section came from guessed split parents (first friendly neighbour without an event; 20-30% of splits sat at < 5 energy). The corrected data uses energy-matched parents (scripts/parents.py): budget.csv / budget-summary.txt (regenerated), m2-varsi-budget.txt (Bane vs VarSi by situation). Keep the text below only as history.

Share of all cell-ticks (split / move / feed / eat / stunned / no event):

| Cell | a | b | c |
|---|---|---|---|
| Bane v2.2 (39) | 14.6 / 21.9 / 1.7 / 0.5 / 0.5 / 60.8 | 5.7 / 6.4 / 5.6 / 1.7 / 0.8 / 79.9 | 1.7 / 1.5 / 14.0 / 2.7 / 0.9 / 79.2 |
| CogSpore - VarSi (17) | 15.0 / 27.0 / 0 / 1.2 / 0.7 / 56.0 | 6.4 / 7.6 / 0 / 2.2 / 1.5 / 82.3 | 1.7 / 1.5 / 0 / 2.7 / 1.9 / 92.2 |
| CogSpore-Siect-F (5) | 15.8 / 28.6 / 0 / 0.9 / 0.4 / 54.4 | 5.6 / 5.4 / 0 / 3.0 / 0.5 / 85.4 | 1.2 / 0.1 / 0 / 5.2 / 0.6 / 92.9 |
| Colossus (24) | 14.7 / 12.6 / 16.4 / 0.9 / 0.3 / 55.1 | 6.7 / 0.4 / 50.6 / 2.3 / 1.6 / 38.5 | 1.6 / 0 / 56.1 / 2.4 / 2.8 / 37.0 |
| medivac (15) | 14.5 / 13.5 / 16.4 / 0.8 / 0.3 / 54.5 | 6.8 / 0.4 / 49.5 / 2.4 / 1.9 / 39.0 | 1.7 / 0 / 67.1 / 2.8 / 2.7 / 25.7 |
| Conviction (5) | 14.6 / 21.3 / 1.6 / 0.6 / 0.7 / 61.1 | 5.2 / 5.4 / 5.6 / 2.3 / 1.3 / 80.2 | 1.1 / 0.8 / 15.6 / 4.0 / 1.4 / 77.1 |

By situation (Bane vs VarSi vs Siect-F):
- "near" = an enemy in the 5x5 but not on an edge. Share of near cell-ticks that had an empty edge, energy >= 5 and no
  event (idle with space): a: Bane 14.3%, VarSi 3.9%, Siect-F 0.8%; b: 11.2, 5.4, 5.5; c: 5.7, 3.9, 3.9. Near cells
  split a: 14.1 / 19.0 / 15.1; b: 8.7 / 11.7 / 13.0. Near cells are 3.9 / 7.4 / 8.4% of Bane's cell-ticks in a / b / c.
- "front" = an enemy on an edge: Bane eat / stunned a 51.7 / 46.6, b 66.4 / 31.0, c 73.8 / 24.4; VarSi b 57.8 / 40.0,
  c 57.8 / 40.4; Siect-F b 81.1 / 14.2, c 87.8 / 9.2.
- Energy at the cap (50, resting earns nothing): Bane c 1.4%, d 21.9%, e 52.3%; VarSi 8.3 / 66.8 / 83.6; Siect-F 11.4 /
  69.7 / 98.2. Bane's interior feeding keeps energy moving; the Yen cells sit at the cap.
- Feeders (Colossus, medivac) feed on half of all cell-ticks from t30, keep most cells under 5 energy, almost never
  move after t30, and fill contested squares with 1-4 energy children (Colossus 1457 such fills t<60, held 78-91%).

## 10. Natural experiments (our own variants)

- Conviction = v2.2 with a 3-instruction blind bite queue: 86% vs Bane 92% in the same era (single-own-cell games);
  early (< 129500) 122/144 vs Bane 165/172; late (>= 129500) 129/149 vs Bane 132/151. vs VarSi 11/17 vs Bane 8/18
  (Fisher p 0.31). Stunned 16-24% after t60 (Bane 28-39%); contested squares about the same as Bane (t60-100 won
  12.9 / lost 21.3 vs Bane 13.3 / 20.7); after a kill it took the freed square less often (13-22% vs Bane 21-53%) and
  had no event 44-65% of the time (its queue bites the empty square).
- Penalty = Conviction + the queue ends with a split into the target's square (not energy-gated): 81%; 7-32% of its
  children in freed enemy squares had <= 4 energy and 10-17% died within 5 ticks (Bane, Conviction 0-2%); vs medivac
  2/10.
- Bane v2.0 -> v2.1 (stored bite): every bite 5 (scan first, no memory) became repeat 4 / first bite 16, and every
  other path +5 (refill 11 -> 16): 82% -> 93% wins (1804 / 203 games; the rival pool also changed between the eras).
  (Corrected 2026-11-12: v2.0's bite was the 5-instruction scan, `git show c263b48:cells/bane2.asm`; confirmed by the
  order markers in section 12, zero violations.) Bane v2.1 -> v2.2 (prey hold only for a diagonal enemy, not any enemy in the 5x5):
  no measurable effect on wins (93% vs 92%, briefs/resume-2026-11-11.md); hold share t30-60 fell from 2-7% to
  0.5-1.3% of cell-ticks.

## 11. Limits of this data

- 38 games in the per-game tables; 17 losses, 10 vs VarSi, 3 vs Siect-F. Siect-F had 34 ladder games at the
  leaderboard read; its behaviour is read from 5 replays.
- "No event" cannot tell a rest from a split or move that failed because the square was taken first.
- Parent of a split = an own neighbour with no other event that tick (first found); rare misattribution.
- The solo potential is our opening from that square, not the rival's own opening.
- Rival behaviour is inferred only from what it did in these replays; rivals change versions without notice.
- Sections 12-14: bite costs come from event order against our own events of known cost; a rival bite between our
  markers is bracketed, not measured to the instruction (5-15 is one class in v2.1 / v2.2 games).

## 12. Exact bite costs from event order (order.csv, order-exact.txt, order-dir.txt; scripts/order.py, order_dir.py)

Method. The engine acts in instruction-count order (fewest first, seeded coin on ties) and the replay logs events in
that order. Some of our events have a fixed count that the replay shows: Bane v2.1 / v2.2 eat on the target the same
cell ate on the previous tick = stored bite 4; split by a cell with no adjacent enemy and energy >= 16 = gate 1, 16;
v2.2 move = walker move 39. Bane v1 / v2.0: every eat = 5, such a split = 11. Conviction: such a split = 14.
Check: in 29 replay batches (pulls 6-9), 4,629,556 marker events, **0 order violations** (every tick's markers are in
non-decreasing cost order). Each rival eat on one of our cells is bracketed by the markers before and after it in the
same tick. Ties are a per-cell coin: a rival bite that costs exactly X lands **between** our cost-X markers.

Share of each rival's eats on our cells by exact cost (v2.1 / v2.2 games; a = t < 100, b = t >= 100; "first" = the
eater did not eat this target on the previous tick, "repeat" = it did; "other" = no marker on one side):

| Rival | kind | w | eats | < 4 | = 4 | 5-15 | other |
|---|---|---|---|---|---|---|---|
| VarSi | first | a | 5,245 | 4.0 | 50.6 | 26.6 | 18.8 |
| VarSi | first | b | 300,887 | 3.6 | 82.4 | 1.6 | 12.4 |
| VarSi | repeat | a | 5,115 | 5.4 | 71.7 | 15.2 | 7.7 |
| CogSpore | first | a | 2,150 | 7.2 | 62.5 | 16.6 | 13.7 |
| CogBloomXT | first | a | 2,409 | 5.3 | 55.5 | 21.5 | 17.7 |
| AtomCrasher | first | a | 736 | 5.4 | 53.3 | 21.2 | 20.1 |
| Aegis | first | a | 585 | 7.0 | 51.1 | 25.5 | 16.4 |
| Siect-F | first | a | 1,453 | 64.5 | 0.0 | 15.5 | 20.0 |
| Siect-F | repeat | a | 4,088 | 99.4 | 0.0 | 0.0 | 0.6 |
| Siect-F | repeat | b | 649,154 | 67.3 | 0.0 | 0.0 | 32.7 |
| medivac | first | a | 874 | 0 | 0 | 79.3 | 20.7 |
| Colossus | first | a | 1,241 | 0 | 0 | 57.3 | 42.7 |
| NomNom2 | first | a | 236 | 0 | 0 | 53.4 | 46.6 |

Bane v1 / v2.0 games (our bites all 5): medivac first bites = 5 exactly in 88-95% (between our 5-cost bites),
Colossus 91-95%; CogBloomXT v4 < 5 in 48-64%, 6-10 in 17-33%; AtomCrasher < 5 63%, 6-10 26%.

Direction of the cost-4 bites (order-dir.txt): VarSi, CogSpore and CogBloomXT bite in exactly 4 **only UP or DOWN**
(LEFT / RIGHT 0.0% of 597,794 / 368,229 / 355,028 such bites); their LEFT / RIGHT bites are all in the 5-15 class.
**(inferred)** They check UP and DOWN as fixed squares first; LEFT / RIGHT cost more.
Siect-F's < 4 bites go in every direction, and per game mostly one way (131188 DOWN 92%, 131198 LEFT 99%, 131245 UP
91%, 131332 UP 47 / RIGHT 53): the side its front faces. With its empty-square behaviour (section 14: eats 85-89%,
not a stuck blind repeat) **(inferred)** a blind bite queue sized so it rarely outlives the target (Conviction's
design without the minimum length), not a direction check: a checked bite in a stored direction needs 4.

What this means for each path of ours (facts from the table; no model):
- Our repeat bite (4) beats medivac, Colossus, NomNom2 (5) and the Yen cells' LEFT / RIGHT bites (5-15) every time,
  ties the Yen cells' UP / DOWN bites (coin), and never beats Siect-F (<= 3).
- Our first bite (16) loses every race against all of these: no main rival's bite costs 16 or more.
- A first bite of 10 or 11 instructions would still lose against costs 3, 4 and 5 (the large majority). It can win
  only against bites in the 5-15 class that cost 11-15: unresolved for the Yen cells' LEFT / RIGHT bites (no marker
  between 4 and 16 in v2.1 / v2.2 games); for CogBloomXT v4 and AtomCrasher (v2.0 games) that class is 6-10.
- Bane v2.0 (all bites 5) against Colossus: duel 57.7 / 41.0 when armed, 41.3 / 56.6 when Colossus was armed (coin
  flips between two 5-cost bites); Bane v2.2: 99.9 / 0.0 and 11.5 / 83.5 (section 13).

## 13. Duels (duel.csv, duel-summary.txt; scripts/duel.py, duel_sum.py)

Two enemy cells that are edge neighbours at tick start, both alive: who bit the other first this tick. Armed = bit
this opponent on the previous tick. Both armed never happens (a cell bitten first is stunned and does not bite).
A stunned cell's memory is unchanged, so its stored bite survives the stun. All games, all ticks:

| Own cell | vs | games | fresh: A first / B first | A armed: A / B | B armed: A / B |
|---|---|---|---|---|---|
| Bane v2.2 | VarSi | 11 | 4.7 / 6.3 | 81.6 / 15.4 | 32.8 / 58.6 |
| Bane v2.2 | Siect-F | 4 | 0.6 / 5.4 | 82.4 / 10.7 | 0.0 / 99.8 |
| Bane v2.2 | Colossus | 7 | 1.5 / 0.6 | 99.9 / 0.0 | 11.5 / 83.5 |
| Bane v2.2 | medivac | 2 | 10.6 / 4.9 | 98.8 / 0.1 | 11.5 / 83.8 |
| Bane v2.2 | CogBloomXT | 5 | 7.2 / 4.4 | 61.6 / 31.5 | 35.9 / 59.3 |
| Bane v2.2 | CogSpore | 2 | 2.2 / 0.9 | 51.1 / 46.6 | 46.2 / 53.1 |
| Bane v2.2 | NomNom2 | 4 | 5.8 / 2.3 | 99.7 / 0.0 | 26.8 / 56.4 |
| Bane v2.2 | AtomCrasher | 3 | 7.5 / 4.2 | 88.1 / 7.3 | 23.9 / 67.0 |
| Bane v2.0 | Colossus | 3 | 1.6 / 2.7 | 57.7 / 41.0 | 41.3 / 56.6 |
| Bane v2.0 | medivac | 3 | 2.1 / 4.3 | 56.3 / 42.0 | 39.7 / 57.4 |
| Conviction | VarSi | 3 | 5.0 / 7.3 | 88.5 / 10.9 | 44.8 / 48.3 |
| Penalty | VarSi | 4 | 4.5 / 4.1 | 85.5 / 12.6 | 51.2 / 42.1 |
| Penalty | Colossus | 10 | 5.9 / 3.4 | 83.8 / 13.2 | 43.6 / 50.8 |

(The rest of "fresh" is neither: both busy with other cells. "B armed: A first" includes escapes where another of our
cells stunned B first.) Reading: once a rival with a cheaper bite has bitten one of our cells, that cell rarely bites
back (stun lock); our 3-instruction queues (Conviction, Penalty) escape VarSi's lock more often than Bane's 4 + 16
(44.8-51.2% vs 32.8%) but Penalty loses Colossus's ongoing exchanges that Bane wins (83.8 / 13.2 vs 99.9 / 0.0, its
queue runs blind past fed targets).

## 14. Blind test, refined (blind.csv, blind-summary2.txt; scripts/blind.py, blind_sum.py)

The square the cell bit last tick is empty now, another enemy is on an edge, the cell is not stunned. self = the
last target died to this cell's bite; other = it died to another cell's bite.

| Cell | self n: eat / none / split | other n: eat / none / split | refill child bitten by the killer on its first live tick |
|---|---|---|---|
| Bane v2.2 | 12,004: 79.2 / 15.2 / 5.6 | 4,743: 86.3 / 8.4 / 5.4 | 31.5% (13,230) |
| Bane v2.0 | 2,182: 94.5 / 4.7 / 0.8 | 602: 98.8 / 0.5 / 0.7 | 87.1% (1,407) |
| VarSi | 12,387: 84.1 / 15.4 / 0.5 | 5,792: 91.0 / 8.2 / 0.8 | 78.5% (17,093) |
| Siect-F | 4,942: 84.8 / 14.8 / 0.4 | 2,229: 89.1 / 10.4 / 0.5 | 76.8% (18,371) |
| Colossus | 11,686: 95.2 / 4.6 / 0.3 | 5,557: 98.7 / 1.1 / 0.1 | 94.0% (22,821) |
| medivac | 12,747: 94.2 / 5.7 / 0.0 | 6,409: 97.7 / 2.3 / 0.0 | 87.4% (22,816) |
| Conviction | 1,905: 9.1 / 83.3 / 7.6 | 1,624: 4.7 / 89.8 / 5.5 | 50.6% (9,124) |
| Penalty | 3,017: 5.0 / 28.3 / 66.6 | 1,612: 8.3 / 36.7 / 55.1 | 34.9% (2,764) |

- Siect-F behaves like a checked biter here (like Bane and VarSi), unlike our blind queues (Conviction none 83-90%).
- Bane v2.2 bites a refilled enemy child on its first live tick 31.5% of the time, v2.0 87.1%, every main rival
  77-94%. Why is not measured (the killer may be stunned, dead, or biting another enemy that tick; when the killer
  bit that square on the tick before, it bites the refill at once 97.3% of the time, n 24,599). **(open)** Whether a
  first bite of 16 (vs v2.0's 5) is the cause.

## 15. Races by our plan, and first-order flips per bite layout (race.csv, race-summary.txt; scripts/race.py)

Our stored bite is rebuilt from the replay: the direction of the cell's last bite, kept through stuns, copied to a
child. Check: our cells' eats go the predicted direction in 4,506,239 of 4,513,687 cases (99.84%). Each tick, each of
our cells with an adjacent enemy has a plan: lock (stored square holds an enemy: 4) or first (bite_tbl scan: 16).
Race = our cell bit its planned target before anything bit it (won), or an enemy bit it first (lost; the cell is
stunned). Share of all races with that rival (a = t < 100, b = t >= 100; v2.1 / v2.2 games):

| Rival | w | races | won: lock / first | lost, plan lock, enemy cost <4 / =4 / 5-15 | lost, plan first (all classes) | lost while planning another target |
|---|---|---|---|---|---|---|
| VarSi | a | 21,976 | 62.3 / 6.9 | 1.1 / 12.0 / 0.2 | 9.7 | 7.6 |
| VarSi | b | 2,012,420 | 74.4 / 0.0 | 0.8 / 17.9 / 0.0 | 0.0 | 6.8 |
| CogSpore | a | 8,886 | 54.7 / 6.2 | 2.6 / 20.9 / 0.4 | 8.8 | 6.0 |
| CogSpore | b | 845,325 | 53.9 / 0.1 | 2.6 / 38.5 / 0.0 | 0.0 | 2.9 |
| CogBloomXT | a | 9,848 | 56.6 / 7.6 | 1.6 / 16.5 / 0.2 | 10.8 | 6.3 |
| CogBloomXT | b | 798,266 | 59.1 / 0.1 | 1.6 / 31.2 / 0.0 | 0.0 | 7.6 |
| Siect-F | a | 5,539 | 12.8 / 3.8 | 23.9 / 0 / 0 | 44.8 | 14.4 |
| Siect-F | b | 622,613 | 1.8 / 0.1 | 21.5 / 0 / 0 (+14.1 unbracketed) | 41.4 | 21.1 |
| Colossus | a | 11,730 | 82.7 / 9.3 | 0 / 0 / 0.3 | 6.6 | 1.0 |
| Colossus | b | 963,576 | 99.6 / 0.3 | 0 / 0 / 0 | 0.1 | 0.0 |
| medivac | a | 8,453 | 82.6 / 10.2 | 0 / 0 / 0.3 | 6.1 | 0.8 |
| NomNom2 | a | 2,991 | 87.8 / 6.4 | 0 / 0 / 0.1 | 5.2 | 0.4 |
| AtomCrasher | a | 3,583 | 70.1 / 6.0 | 0.6 / 4.7 / 0.1 | 5.3 | 13.3 |
| Aegis | a | 3,256 | 69.2 / 7.6 | 1.1 / 10.6 / 0.1 | 7.0 | 4.2 |

- Against the Yen cells the largest lost share is our stored bite losing the coin to their 4-instruction UP / DOWN
  bite: 12-21% of all races before t100, 18-39% after. First-bite losses are 9-11% before t100 and ~0 after.
- Against Colossus, medivac, NomNom2 we lose only first-bite races (5-7% before t100, ~0 after): our 4 beats their 5.
- Against Siect-F we lose 66-86% of races at every stage (their bite <= 3).

First-order flips (net % of all races with that rival; [low .. high] where the 5-15 class matters; counts races, not
the game after them; "lost" side counts only won lock races where the enemy was armed on our cell, a lower bound):

| Rival | w | v2.3a (4 / 11) | scan-first (5 / 5) | queue3 (3 / 16) | queue3 + first 11 |
|---|---|---|---|---|---|
| VarSi | a | 0 .. +2.3 | -8.8 .. -6.8 | +9.6 | +9.6 .. +11.9 |
| VarSi | b | 0 .. +0.01 | -14.7 .. -13.7 | +14.1 | +14.1 |
| CogSpore | b | 0 .. +0.01 | -30.2 .. -30.1 | +31.4 | +31.4 |
| CogBloomXT | b | 0 .. +0.01 | -24.3 .. -24.0 | +24.8 | +24.8 |
| Siect-F | a / b | 0 .. +1.2 / 0 | +0.6 .. +1.2 / 0 | +12.0 / +10.8 | +12.0 .. +13.2 / +10.8 |
| Colossus | a / b | 0 / 0 | +1.6 / 0 | 0 / 0 | 0 / 0 |
| medivac | a / b | 0 / 0 | +2.1 / +0.5 | 0 / 0 | 0 / 0 |

- "queue3" = every lock situation bites in 3 instructions. A checked bite in a stored direction needs 4 (section 3),
  so 3 means a blind bite queue (Conviction's mechanism). The table does **not** include the queue's costs: blind bites
  into a square whose target died (Conviction: no event 83-90% in that case, section 14), +3 on every path behind the
  queue (lock 7, first bite 19, refill 19 in a plain stack), and lock situations the queue does not cover then cost 7,
  which loses to Colossus / medivac (5) where Bane wins today.
- Natural experiment for queue3: Conviction (blind queue 3, minimum length 3, scan 19, +3 on all paths) did better than
  Bane only vs VarSi (11/17 vs 9/21) and worse vs CogSpore (16/29 vs 23/29), Colossus (10/26 vs 18/29), medivac (13/19
  vs 21/23); overall 86% vs 92%.
- v2.3a (first bite 11, all other non-lock paths -1, no behaviour change) gains at most 0-2.3% of early races and ~0
  later; it costs nothing measurable.
- **Correction 2026-11-12 (built):** the 11 / -1 layout needs `cmove` (keeps al = 0 on a stored-bite miss), which is
  not on the site allow-list (only cmova / cmovae are seen running). The built v2.3a (cells/gen_bane3.py) uses only
  allowed instructions: stored-bite bytes swapped ([2] action, [3] square), one 16-bit load from lock2_tbl and one
  16-bit store: **first bite 12, every other path unchanged** (slow path still starts at 10, stored bite 4). Its race
  flips are at most the v2.3a column above (an 11-instruction enemy bite is now a tie, not a win).

## 16. Blind-queue sizing on our real bite chains (queue.csv, queue-summary.txt; scripts/queue_chains.py, queue_sum.py)

Chain start = one of our cells (v2.1 / v2.2 games) eats an enemy T that it did not eat on the tick before (831,049
chains). Recorded: T's energy at the start of that tick (e0, what our cell sees), our other cells next to T (nf), and
the horizon H = later ticks on which T is still alive on the same square at tick start (capped at 12). A queue armed
at the chain start with k blind bites (3 instructions each, view not read) hits T min(k, H) times and bites an empty
or refilled square max(0, k - H) times. Rules: conviction k = clamp(ceil((e0 - 2) / 2), 3, 7) (Conviction's queue);
need = the same with minimum 0; shared = need with every visible attacker (1 + nf) counted; shared-1 = shared minus 1;
one = 1 bite if shared >= 1. Cover = hits / sum of H (share of T's remaining ticks bitten at 3).

| Rival | w | chains | mean H | T died in horizon | conviction: k / wasted / cover | need: k / wasted / cover | shared-1: k / wasted / cover |
|---|---|---|---|---|---|---|---|
| ALL | a | 26,414 | 4.9 | 76% | 4.0 / 26.4% / 59.9% | 3.1 / 9.3% / 56.5% | 2.1 / 3.7% / 41.8% |
| ALL | b | 804,635 | 11.5 | 6% | 6.8 / 1.2% / 58.4% | 6.7 / 0.6% / 58.3% | 5.7 / 0.2% / 49.8% |
| VarSi | a / b | 5,519 / 275,392 | 6.0 / 12.0 | 69% / 1% | 19.0% / 0.1% wasted | 5.1% / 0.0% wasted | 2.0% / 0.0% wasted |
| CogSpore | a / b | 2,331 / 197,997 | 7.4 / 12.0 | 55% / 1% | 13.7% / 0.1% | 3.9% / 0.0% | 1.5% / 0.0% |
| CogBloomXT | a / b | 2,520 / 172,217 | 6.3 / 11.9 | 65% / 1% | 18.6% / 0.2% | 5.6% / 0.1% | 2.0% / 0.0% |
| Siect-F | a / b | 278 / 2,066 | 8.5 / 12.0 | 38% / 0% | 12.0% / 0.1% | 1.5% / 0.0% | 0.8% / 0.0% |
| Colossus | a / b | 2,248 / 7,171 | 4.0 / 6.3 | 86% / 64% | 35.5% / 24.8% | 15.9% / 14.6% | 7.9% / 4.5% |
| medivac | a / b | 1,719 / 12,364 | 3.7 / 7.2 | 89% / 67% | 32.8% / 12.8% | 15.9% / 8.0% | 8.4% / 4.6% |
| NomNom2 | a / b | 482 / 8,359 | 4.2 / 4.9 | 80% / 78% | 36.5% / 28.4% | 13.8% / 16.6% | 2.3% / 4.0% |

(Wasted = share of blind bites that land on an empty or refilled square; a refilled square can be our own child.
Weak and old rivals, e.g. Hunter, shrimp, Sho, zergling: H 1-3, 98-100% die, wasted 38-68% conviction / 17-29% need.)

- Before t100 targets die fast (76% within the horizon, mean H 4.9): Conviction's minimum of 3 wastes 26% of its
  blind bites; "need" (no minimum) covers almost the same share of T's ticks (56.5 vs 59.9%) with a third of the waste.
  **(inferred)** Conviction's minimum of 3 explains part of its early cost; section 14 showed the same from the other
  side (Conviction: no event 83-90% when its target square was empty).
- After t100 the Yen fronts and Siect-F are stalemates: T is still there 12 ticks later in 99-100% of chains, and any
  queue rule wastes <= 0.2% of its bites. Against these rivals a queue is first-order free in wasted bites, and these
  are the races section 15 says a 3-instruction bite flips (+11-31% of races in window b).
- Against Colossus, medivac, NomNom2 targets die or move often in both windows (H 4-7): a queue wastes 8-36% of its
  bites (need: 8-17%), and gains no races there (our checked 4 already beats their 5, section 15).
- Cover in window b is about 58% for every k-capped rule only because k <= 7 against H capped at 12; the measure scores
  one arming per chain start, not a queue that re-arms while T stays.
- Case against / limits: first-order only (T's survival is the real one under v2.2's 4-instruction bites; a faster
  bite changes who is stunned and so H); "empty or refilled" does not separate our own child from an enemy refill;
  nf counts only our cells that T can see beside it; this measures waste only, not the +3 a queue adds to every path
  behind it in a plain stack (section 15), which is the larger known cost.
