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
  Update 2026-11-08 (docs re-review): the Reference states the rule outright, "The engine counts every instruction" (p.3).
- Cells 150 and 151 were created by a scripted POST (fetch) to /cells/new. That build said only
  "Built OK." and did NOT put them on the ladder; the browser form's submit does ladder a new cell.
- calib-e-jexit (cell 150 id reused, created 2026-11-08 by scripted POST, not laddered; Sandbox match 99887 vs Idle): `mov al,ACT_REST / jmp EXIT_ADDR` = 2 (2) insns/call, 0 faults, energy 50. => a call may end with a jump to EXIT_ADDR instead of ret (1 instruction either way). Clears Covetous's `jnz EXIT_ADDR` bite exit. Sprint at that time: rating 1355, 223 games.
- Re-uploaded 2026-11-08 for a full site history, all by scripted POST, none laddered: calib-a-rest, calib-b-jmp, calib-c-rax, calib-d-rep (plus calib-e-jexit). The site rate-limits cell creation: two POSTs 4 s apart got HTTP 429; 30 s apart worked. A built page's text can mention the ladder without laddering, so check the My cells list, not the response text.
- Covetous (cell 155): built by scripted POST; Sandbox 99921 (16x16) vs Sprint, Hunter, Walker: 1st, pop 255, all others 0 by tick 315, 0 faults, insns/call avg 41 max 58; put on the ladder with the user's approval via the cell page's "Put on the ladder" button.
- Scourge (cell 156): source (17 KB) loaded into the page through a temporary <input type=file> + file_upload, then scripted POST; serving it from 127.0.0.1 froze the tab (Chrome local-network prompt). Sandbox 101671 (16x16) vs Covetous, Sprint, Hunter: 1st pop 186, Covetous 70, 0 faults, insns avg 43 max 53; then laddered (pre-approved). Covetous then 1526 after 314 games, Sprint 1238 after 547.
- CPU-feature probes 2026-11-08 (cells/calib/f..m, each `<insn> / mov al,ACT_REST / ret`, scripted POST, not laddered, Sandbox vs Idle): INVALID (invalid_insn at rip 0x100000 every call, colony stays at 10): popcnt (103568), SSSE3 pshufb (g), SSE4.1 ptest (103571), SSE4.2 crc32 (m), BMI1 andn (i), BMI2 pext (103574), AVX2 ymm vpcmpeqb (103577). WORKS: AVX 128-bit VEX vpcmpeqb xmm (k): 3 (3) insns, 0 faults, energy 50. Site author: qemu + SSE2/SSE3 officially supported, others may work. Sandbox runs need >= ~15 s between them ("please wait 5s" refusals at 10 s).
- VEX follow-ups 2026-11-08 (cells/calib/n..p): VEX vpshufb xmm (SSSE3 op) INVALID; VEX vptest xmm (SSE4.1 op) INVALID; VEX vpcmpeqb xmm with an UNALIGNED memory operand ([rdi+VIEW_CELLS+7]) WORKS, 3 (3) insns, 0 faults. So: the AVX encoding is accepted only for SSE2/SSE3-level operations, but it removes the alignment rule and allows a 3-operand load+compare in one instruction.
- Register probes 2026-11-08 (cells/calib/q, r; Sandbox vs Idle, not on the ladder): calib-q-xmmzero 22 (22) insns, 0 faults -> xmm0..xmm15 all ZERO at entry on every call; VEX vpxor/vpcmpeqb reg-reg/vpmovmskb accepted. calib-r-gprzero 15 (15) insns, 0 faults -> rbx, rcx, rbp, r8..r15 all ZERO at entry (rax already known zero).
- VEX semantics 2026-11-08: Woe (cell 171, VEX variant of Scourge) built, 0 faults, but died in both Sandbox games (104123 vs Scourge/Covetous/Contagion: peak 4; 104128 vs Scourge/Hunter: peak 5, Scourge 255). calib-s-vexsrc (Sandbox 104136): `vpcmpeqb xmm2, xmm0, xmm1` gave bad_action every call -> the site's QEMU computes dest == src2 and ignores the first source (same bug as Unicorn 2.1.4). Only the form with destination = first source is reliable, e.g. `vpcmpeqb xmm0, xmm0, [rdi+VIEW_CELLS+7]` (unaligned memory still OK, probe p). Woe/Conceit/Endemic are broken on the site: do not submit.
- Failed-action income 2026-11-08: Rules page says "Resting is the only income. A tick spent doing anything else is a tick without the 1" and "Nothing happens" for splits/moves into walls or occupied squares. calib-t-failedeat (always eats UP at nothing; Sandbox 104248): energy stayed 10 for 500 ticks, 0 faults, vs Idle 50 -> a failed action earns 0. The sim's default (idle_gain_prob = 0) is correct. Docs now searchable: pypdf installed (user site-packages; run python without -I).
- Complacency (cell 174, Scourge without the prey hold) Sandbox 2026-11-08: 104753 vs Scourge/Covetous/Contagion: 1st, pop 88 (Scourge 82), 0 faults, insns avg 39 max 53; 104755 vs Scourge/Hunter: 2nd, pop 94 (Scourge 162), 0 faults, avg 39 max 53. Builds and runs as checked locally; not on the ladder.
- Ladder change 2026-11-08 (user-approved): Complacency (174) put on the ladder, Covetous (155) taken off (retired, not deleted); ladder = Scourge, Contagion, Complacency. Done by scripted POST to /cells/<id>/activate and /deactivate (the cell page's own buttons).
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

## Replays are fully machine-readable (verified on match 98753)
- The match page loads `/api/matches/<id>/replay` (gzip, binary "CHR2", ~44 MB raw). The page's own
  `CellHackViewer.decode(arrayBuffer)` returns: `h` (version 4, ruleset 9, w/h 64, maxTicks 3000, seed,
  colony cell ids, energyScale 15, keyframe every 50 ticks), `keyframes[t]` = list of {id, c, x, y, e},
  `ticks[t]` = {pop[4], energies (Uint8Array), events}, `end` = {placement, pop, reason, ticksRun}.
- Event kinds: k1 birth {id, c, e, x, y}; k2 move {id, x, y}; k3 death {id}; k4 eat {id eater, id2 target,
  amt}; k5 feed {id, id2, amt}. Colony of any id comes from keyframe 0 plus k1 births.
- Events within a tick are in turn order (check: Sprint never eats after its own split in a tick, as eat 6
  < split 19+). So relative initiative between colonies can be measured from the event order.
- Method: run analysis JS in the match page (Claude in Chrome) and return only numbers; raw viewer.js
  source cannot be returned (the tool's output filter blocks it).

## START POSITIONS ARE RANDOM, NOT CORNERS (match 98753)
Starts: Brawler (10,61), Walker (23,30), Sprint (45,21), AtomPush (13,41). The docs' "one per corner"
(cellhack.inc comment) is wrong or out of date for the ladder. (Update 2026-11-08: the Rules pages never say corners; only that comment does.) Every corner/home/outward assumption in
designs.md and the sim (CORNER_ORDER, start_inset) must change: starts can be mid-board with four open
directions, and colonies can start close to each other.

## Match 98753 analysis (AtomPush 1st 3258, Brawler 2nd 838, Sprint 3rd, Walker 4th)
| | Brawler | Walker | Sprint | AtomPush |
|---|---|---|---|---|
| splits | 1303 | 782 | 2150 | 4747 |
| moves | 0 | 1080 | 0 | 0 |
| eats of enemies | 164712 | 0 | 1871 | 82971 |
| feeds (all to friends) | 1837605 | 0 | 0 | 826729 |
| deaths | 466 | 783 | 2151 | 1490 |
| mean energy t=200 / 500 / 1000 | 10.8 / 11.8 / 11.5 | dead | 46.7 / 48.6 / 47.3 | 38.2 / 47.6 / 48.5 |
Population (Brawler/Walker/Sprint/AtomPush): t50 170/125/253/386; t100 355/186/878/1019;
t200 583/0/1532/1921; t500 693/0/957/2444; t1000 728/0/198/3170; t2999 838/0/0/3258.

Initiative from event order (pairs of eats in the same tick, who came first):
- Brawler before Sprint 88120, Sprint before Brawler 63. => Brawler's bite path is <= 5 (a tie at 6
  would be ~50/50).
- AtomPush before Sprint 78932, Sprint before AtomPush 13353 (85/15). => AtomPush bites below 6 on most
  paths, above 6 on some.
- AtomPush vs Brawler: 2.07M vs 2.56M, interleaved => roughly equal bite counts (both ~5 or mixed).
- Both rivals' feeds always come after Sprint's eats => their feed paths are > 6 (slow path), as expected.
Readings:
- The top cells bite in 5 or fewer instructions (consistent with a lock); our 6 loses every contact.
- Feeding is massive: Brawler issued ~11 feeds per eat, AtomPush ~10. Both keep the front supplied.
- Sprint's interior sat at ~48 energy (capped, idle) while its front was eaten: it lost ~1.3 cells/tick
  from t=200 to t=1000. Exactly the "unfed front collapses" pattern from the sim.
- Brawler survives at a mean energy of only ~11 with a <=5 bite and heavy feeding; it held 2nd place.
- AtomPush out-grew Sprint early (386 vs 253 at t50), so its grab is faster than split-at-5.
- Random mid-board starts make the grab ~4x faster than the corner-start sim (Sprint 878 at t100 here vs
  284 in the corner sim).

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
