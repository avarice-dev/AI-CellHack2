# Site observations, 2026-11-08 (UTC), read via Claude in Chrome

## Site mechanics (verified)
- "Save and build" on a new cell puts it on the ladder immediately ("Built OK. It is now on the ladder.").
  A ladder game starts within seconds. Cell page then offers "Take off the ladder" (rating kept) and "Delete"
  (raises a confirm() dialog).
- The Sandbox only runs saved cells (own cells or the 5 sample bots), 16x16, 500 ticks, up to 3 opponents
  or empty corners. "Nothing here affects the ladder." So any calibration cell must be saved first, which
  ladders it.
- Match page columns: Colony, Player, Place, Final pop, Peak, Energy, Faults, Insns/call shown as
  "avg (max)", Rating before -> after. Fault log only for your own colonies.
- Leaderboard shows per cell: rating, games, wins, avg place, average insns/call; filters Hand-crafted /
  AI-assisted, Cells / Players, show retired.

## Calibration results
- calib-a-rest (cell 148, `mov al,ACT_REST / ret`): 2 (2) in ladder match 98728. => `ret` counts.
- Walker in the same match: 7 (9). Walker's longest path (move, e<6) is 9 only if the taken `jb` counts
  (8 without). => taken jumps count. The plan's convention (every executed instruction) is confirmed.
  Consequence: F6 = 6, post/checked lock = 5, blind lock = 3. Design C's lock edge over F6 is real.
- calib-c-rax (cell 150, sandbox match 98751 vs Idle): 4 (4), no faults, ended at 50 energy. => rax is 0
  at entry on every call (the 3-instruction blind lock `or al,[rdx] / jz / ret` is possible).
  Same match: Idle placed 1st on equal population and energy => fewer total instructions breaks the tie.
- calib-d-rep (cell 151, sandbox match 98755): 105 (105). => `rep stosb` counts per iteration plus one
  (100 iterations + 5). No bulk-work shortcut for anyone. Matches the local Unicorn count exactly (2, 4,
  105 all agree), so the stage-2 emulator's instruction counts can be trusted.
- Cell B (taken jump) was not run: Walker's max of 9 already settles it.
- Cells 150 and 151 were created by a scripted POST (fetch) to /cells/new. That build said only
  "Built OK." and did NOT put them on the ladder; the browser form's submit does ladder a new cell.
- calib-a-rest accidentally played 1 ladder game (placed 4th, rating 1000 -> 912) before it was taken off.
  It is retired now.

## Match 98728 (ladder, 4 colonies)
| Cell | Player | Place | Final pop | Peak | Insns/call avg (max) |
|---|---|---|---|---|---|
| Brawler v2 | Striker | 1 | 4095 | 4095 | 23 (24) |
| Bulwark | myles777 | 3 | 0 | 25 | 28 (55) |
| Walker (bot) | | 2 | 0 | 2184 | 7 (9) |
| calib-a-rest | us | 4 | 0 | 1 | 2 (2) |
Brawler v2 took 4095 of 4096 squares: a strong human cell eliminates everyone.

## Sprint on the ladder (cell 149, put on with the user's approval, 2026-11-08 00:09 UTC)
| Match | Sprint place | Sprint peak / final | Sprint insns avg (max) | Winner (final pop, energy, insns) |
|---|---|---|---|---|
| 98746 | 2 | 1755 / 0 | 18 (21) | rooby, patrickHakun (4095, 204240, 81 (101)); Noob++ 3rd, Medic 4th |
| 98753 | 3 | 1543 / 0 | 18 (21) | AtomPush, HammerSpb (3258, 158251, 36 (47)); Brawler 2nd (838), Walker 4th |
Readings: no faults; insns as modelled. Sprint grabs fast (peaks 1500-1750) but is wiped out: it never
feeds and its children are thin, which fits the sim indication that unfed fronts collapse. The winners
end at about 49-50 energy per cell (204240 / 4095), so they keep their whole colony fat. Their averages
(36-81) say nothing about their front path; replays are needed to see how they beat a 6-instruction bite.

## Leaderboard (active cells, 2026-11-08 ~00:10 UTC)
| # | Cell | Player | Rating | Games | Wins | Avg place | Insns/call |
|---|---|---|---|---|---|---|---|
| 1 | AtomCrasher v7 | HammerSpb | 1542 | 16331 | 11943 | 1.30 | 36 |
| 2 | AtomPush v5 | HammerSpb | 1503 | 16419 | 12692 | 1.25 | 35 |
| 3 | rooby v5 (AI) | patrickHakun | 1365 | 6484 | 3238 | 1.66 | 77 |
| 4 | Brawler v2 | Striker | 1350 | 7069 | 3400 | 1.72 | 21 |
| 5 | Bouncer | Striker | 1295 | 7008 | 3594 | 1.69 | 21 |
| 6 | Brawler | Striker | 1229 | 7172 | 3262 | 1.77 | 21 |
| 7 | Noob++ v2 | Assembler | 1215 | 18871 | 8433 | 1.76 | 89 |
| 8 | Noob+ v3 | Assembler | 1184 | 20634 | 9229 | 1.80 | 22 |
| 9 | Aegis v18 | myles777 | 1118 | 21989 | 8504 | 1.86 | 34 |
| 10 | gemAlert_v4 (AI) | gschweers | 1033 | 1894 | 239 | 2.44 | 34 |
| 11 | Noob | Assembler | 913 | 28452 | 9602 | 2.13 | 14 |
| 12 | Bulwark v5 | myles777 | 811 | 17658 | 0 | 2.79 | 27 |
| 13 | zergling v44 | andrew | 755 | 17644 | 1136 | 2.70 | 19 |
| 14 | gemAlert_v3 | gschweers | 747 | 1961 | 31 | 2.83 | 39 |
| 15 | Hunter (bot) | | 683 | 34192 | 8832 | 2.52 | 19 |
| 16 | squirtle | patrickHakun | 665 | 7034 | 531 | 3.07 | 19 |
| 17 | Walker (bot) | | 502 | 34178 | 999 | 3.24 | 7 |
| 18 | Medic (bot) | | 455 | 34162 | 518 | 3.29 | 9 |
| 19 | Random (bot) | | 356 | 34229 | 79 | 3.30 | 12 |
| 20 | choochoo v2 | andrew | 1 | 24081 | 0 | 3.93 | 13 |

Readings:
- Small field: 20 active cells, about 10 human players, 4 bots (Idle not active). A 4-colony match usually
  holds 2-3 humans and 1-2 bots.
- Averages are dominated by slow paths and do not reveal front-path counts. The top two average 35-36,
  so they spend instructions on slow-path logic. Their front paths need replays or a probe cell.
- The top cells win 73-77% of games (avg place 1.25-1.30). Beating HammerSpb's cells is the real target.
- Hunter averages 19, consistent with its split 20 / rest 17 paths (most cells sit in the interior).
