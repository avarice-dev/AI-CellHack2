# CellHack2 ladder data, 2026-11-08 (for review)

Collected through the logged-in site with Claude in Chrome, gently: 10 match-list pages (398 finished
ladder matches, ids 98432-98829), 13 replay downloads (~12 MB each, 12-20 s apart), a few small match
pages and the leaderboard. Earlier facts (calibration, first replay, site mechanics) are in
`data/site-observations-2026-11-08.md`. Replays were decoded with the site's own `CellHackViewer.decode`
and analysed in the page; event order within a tick is turn order (verified).
Current pacing (2026-11-08): see "Pacing rules for the site" in `architecture/data-pulls.md`.

## 1. Headline findings
1. **Every strong rival checks directions in a fixed order (Hunter-style static checks).** Against Sprint,
   which bites in 6 in every direction, each rival has one direction where it always bites first (cost
   <= 5, i.e. 4), one direction that is close to a tie (50-65%, i.e. 6), and two where it always bites
   later (>= 7, i.e. 8 and 10). Table in section 4. Nobody seen so far has a flat or locked front.
2. **Sprint (flat 6, no feeding, no lock) is rated 1305, 5th of ~20, with 12 wins in 24 games.** It beat
   rooby, Brawler, Brawler v2, Bouncer and Aegis at least once. It wins when its contacts fall in the
   rivals' slow directions and its neighbours are weak; it loses to HammerSpb's cells and when it meets a
   rival's fast direction.
3. **The upset winners all run a "pump"**: thin interior (mean energy 14-22), fat front (38-49), 30-80
   feeds per bite. Bouncer, Brawler v2, Aegis and Noob+ beat HammerSpb's cells this way.
4. **HammerSpb's cells win on economy, not bite speed.** Fat colonies (mean ~47-49), moderate feeding
   (3-15 feeds per bite), fast grab. Their bites are the same static-order type as everyone else's.
5. **Land is decided by tick ~300-500.** In most matches populations barely move after tick 500 (section 3).
6. **Starts are random squares** (section 5), often mid-board and sometimes close together.

## 2. Win rates over 398 ladder matches (wins / games in the sample)
AtomPush 61/79, AtomCrasher 62/83, Bouncer 43/82, rooby 37/71, Brawler v2 40/77, Sprint 8/16 (now 12/24),
Noob+ 33/76, Brawler 31/75, Aegis 27/73, Noob++ 18/72, Noob 16/83, gemAlert_v4 8/75, Hunter 7/79,
squirtle 4/80, zergling 1/81, gemAlert_v3 1/81, Medic 1/83, Bulwark 0/79, choochoo 0/81, Walker 0/80,
Random 0/85.

Selected head-to-head (both present; wins each, other = a third colony won):
AtomCrasher vs AtomPush 5/5/0 (n10); AtomPush vs Brawler 14/2/4 (n20); AtomCrasher vs Brawler 12/4/1;
AtomCrasher vs Bouncer 12/3/1; AtomCrasher vs rooby 12/1/2; AtomPush vs rooby 7/2/2; Bouncer vs rooby
3/8/1; Aegis vs rooby 1/9/6; Brawler v2 vs rooby 5/1/2; Bouncer vs Brawler v2 6/5/5; Aegis vs Bouncer
1/8/2. HammerSpb lost 29 of the 398 matches it played in (upsets): winners Brawler v2, Bouncer, Aegis,
Brawler, Noob+, rooby, Noob++.

Leaderboard 2026-11-08 ~00:40 UTC: AtomCrasher v7 1514, AtomPush v5 1498, rooby v5 1395, Bouncer 1317,
Sprint 1305 (24 games), Brawler 1261, Noob++ v2 1220, Aegis v18 1181, Brawler v2 1154, Noob+ v3 1121,
gemAlert_v4 951, Noob 914, Bulwark v5 810, Hunter 765, ... Average insns/call: HammerSpb 35-36,
rooby 77, Striker's cells 21, Noob++ 89, Noob+ 22, Aegis 34, Noob 14, Sprint 19.

## 3. Ten instructive matches (why each was chosen, what it shows)
Columns per colony: place, final pop, peak, insns/call avg (max), splits, deaths, eats of enemies,
feeds, feeds per eat, mean energy at t200 / t1000, mean energy of front cells at t1000 (x count).

**98748 — the four strongest-rated together (AtomPush 1st).**
| Cell | pl | final | peak | insns | splits | deaths | eats | feeds | f/e | en200/1000 | front1000 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AtomPush | 1 | 2230 | 2350 | 36 (47) | 2971 | 742 | 109.5k | 371k | 3.4 | 40.5/49.1 | 35.9 x61 |
| AtomCrasher | 2 | 1604 | 1620 | 35 (47) | 14620 | 13017 | 97.3k | 650k | 6.7 | 43.8/47.3 | 30.1 x62 |
| Brawler v2 | 4 | 0 | 441 | 19 (23) | 1294 | 1295 | 5.5k | 64.6k | 11.8 | 7.6/- | - |
| Brawler | 3 | 256 | 375 | 19 (24) | 3848 | 3593 | 77.8k | 440k | 5.7 | 13.2/14.6 | 37.8 x33 |
Bite-first (same-tick eat pairs, % first): AtomPush>AtomCrasher 58%, AtomPush>Brawler 56%,
AtomCrasher>Brawler 54%, Brawler v2>Brawler 72%. Pop t50 350/289/184/161, t100 1109/805/334/344,
t200 2181/1107/382/303, t500 2299/1532/4/256, end 2230/1604/0/256. Grab decided it; nothing moved after ~t500.

**98635 — HammerSpb pair vs rooby and Brawler (AtomCrasher 1st).** AtomCrasher 1664 (front energy 48.3,
feeds 1 per eat, 118 deaths), rooby 1257 (feeds almost never: 3.9k feeds for 187k eats, mean 49),
AtomPush 1172 (15.5 feeds/eat, 9708 deaths), Brawler 0. Bite-first: rooby>AtomPush 73%,
rooby>AtomCrasher 70%, Brawler>rooby 39%. Pop end 0/1172/1257/1664; t500 already 124/990/1386/1593.

**98766 — upset: Brawler v2 beats AtomPush (3961 vs 134).** Brawler v2: 7.93M feeds for 118k eats (67
per eat), mean energy 9.9 (t200) / 18 (t1000), front cells 40.4. Bite-first Brawler v2>AtomPush 66%.
AtomPush was ahead at t100 (686 vs 354) and still 891 vs 722 at t200; Brawler v2 overtook by t500
(1611 vs 944) and ate it down to 134. **The only match seen where a front moved a lot after t500.**

**98790 — upset: Aegis wipes everyone (4095).** Aegis: 5.95M feeds / 78k eats (76 per eat), mean 16.6 /
20.8, front 38.1. Bite-first Aegis>AtomCrasher 93%, Aegis>rooby 91%. Aegis led from t50 (391 vs 173).

**98711 — upset: Noob+ beats AtomCrasher (1822 vs 1367).** Noob+: 4.74M feeds (30 per eat), front
energy 49.1, only 127 deaths. AtomCrasher's front starved: front energy 4.5 at t1000, 14282 deaths,
2.44M feeds for only 10k eats. rooby bit first in 100% of pairs vs Aegis and Noob+ in this match.

**98797 — upset: Bouncer beats AtomCrasher (4080 vs 14).** Bouncer: 8.98M feeds (82 per eat), interior
13.8, front 45.7, 436 deaths. Bite-first Bouncer>AtomCrasher 87%. Pop t200 2263 vs 1395; Bouncer then ate
AtomCrasher steadily (1239 at t500, 986 at t1000, 14 at the end).

**98777 — Sprint wins (2356) over rooby (1740), Noob++, squirtle.** Sprint bit first vs Noob++ 96%,
squirtle 100%, rooby 62%. Noob++ grew fastest (2286 at t200) but Sprint ate it: 2695 kills.

**98818 — Sprint wins 4095 at tick 995 over Brawler, gemAlert_v3, Medic.** Sprint bit first vs Brawler
76% (Brawler's contacts were mostly in its slow directions here), gemAlert_v3 100%. Match ended early
(one colony left).

**98768 — Sprint vs AtomCrasher (AtomCrasher won).** Used for the direction profile (section 4).
**98772 — Sprint vs Brawler v2 (Brawler v2 won).** Used for the direction profile.
**98753 — Sprint, Brawler, AtomPush, Walker (AtomPush won).** First replay analysed (earlier file).

## 4. Bite speed by direction, measured against Sprint (flat 6)
% = share of same-tick eat pairs where the rival's eat came before Sprint's. 100% => rival's path <= 5 in
that direction; ~50-65% => 6 (tie, random order); 0% => >= 7. n = rival eats in that direction.
| Cell (match) | UP | RIGHT | DOWN | LEFT | Reading |
|---|---|---|---|---|---|
| Brawler (98753) | 100% n164657 | 0% n12 | - | 51% n43 | U first, L second |
| Brawler (98818) | 100% n5724 | 0% n14343 | 0% n6516 | 65% n1456 | U 4, L 6, R/D >= 8 |
| Brawler v2 (98772) | 100% n34808 | 0% n477 | - | 58% n224 | U 4, L 6 |
| AtomPush (98753) | 0% n2209 | 100% n67733 | 0% n13016 | 64% n13 | R 4, L 6 |
| AtomCrasher (98768) | 0% n10261 | 100% n5819 | - | 61% n15815 | R 4, L 6 |
| rooby (98777) | 100% n129 | 53% n75827 | 0% n25224 | 0% n389 | U 4, R 6 |
| Noob++ (98772, 98777) | 0% | 0% | 100% | 0% | D first |
| squirtle, gemAlert_v3 | 0% | 0% | 0% | 0% | slower than 6 everywhere |
| Hunter (98772) | | | | 0% n845 | L is its 4th check (16): method check |
Implications: a flat 5 (our checked lock) beats each of these cells in 3 of 4 directions and loses only
to its first direction (4). A blind lock (3) beats all of them everywhere. Since starts are random,
which direction a rival's front faces is luck; a static-order cell is strong only on one side.
Relative bite tests between rivals agree: e.g. Bouncer>AtomCrasher 87%, Aegis>AtomCrasher 93% in the
matches they won (their contacts fell in their fast directions).

## 5. Start positions (keyframe 0), 10 matches
98748 (6,40) (38,7) (50,6) (3,15); 98635 (35,16) (39,2) (18,38) (35,42); 98766 (12,16) (37,26)
(61,38) (54,25); 98790 (61,18) (58,46) (46,53) (53,11); 98711 (25,42) (13,22) (20,56) (10,29);
98797 (21,33) (5,52) (49,46) (18,18); 98777 (57,5) (32,59) (27,19) (35,4); 98818 (14,53) (59,58)
(33,10) (10,22); 98768 / 98772 not recorded; 98753 (10,61) (23,30) (45,21) (13,41).
Starts can be near edges (x or y of 2-6) and near each other (e.g. 98777: (57,5) and (35,4)).

## 6. What this suggests (for the reviewer to test, not settled)
- Our planned 5-instruction lock is enough to beat every observed rival in 3 directions out of 4; a
  pre-armed lock also wins first contact. A 3-instruction blind lock would beat everyone everywhere,
  at the cost of never exiting.
- Feeding style decides upsets: the pump (thin interior, fat front, 30-80 feeds per bite) beats the fat
  economy cells when its bite is faster on the contact side.
- The grab still decides most matches; most populations are frozen after t300-500.
- Sprint's success with no feeding at all suggests a fast, cheap grab plus a flat bite already beats much
  of the field; the round 3 kernel adds the lock and feeding on top.
