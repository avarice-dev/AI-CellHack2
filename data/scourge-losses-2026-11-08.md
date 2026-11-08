# Scourge: who it loses to and how (pull 3, 2026-11-08)

Data: Scourge's newest 100 finished ladder games (matches 103128-103747, `data/pull3/matches-scourge-2026-11-08.json`,
from the rjclay match list plus one match page per game, 6 s apart) and 15 loss replays decoded offline
(`data/pull3/replays/`, git-ignored, 278 MB; decoder `tools/pull2/mine.py` with `CH_PULL=pull3`, 0 keyframe mismatches in
all 15; outputs `data/pull3/mining/`). Tables: `python -I tools/pull3/tab.py` and `python -I tools/pull3/losses.py`.

## Findings

1. **Overall: 74 of 100 won, places 74/23/3/0, never 4th.** Rating 1526 -> peak 1649 (after match 103542) -> 1506.
   Before the peak 55/68 won (81%), after it 19/32 (59%). The 26 losses are spread out: AtomPush 5, Covetous 5 (our own
   cell), AtomCrasher 4, then Aegis, Brawler v2, Noob++, Noob+, rooby 2 each, Brawler 1, Contagion 1 (ours). 7 of the
   13 losses after the peak went to mid-field cells (Noob+, Noob++, Aegis, rooby, Brawler v2). Why the loss rate rose
   is not shown by this data (rival versions were not re-checked; could be variance: Fisher exact p = 0.03).
2. **Losses are decided by the land grab, by t100-t200, not by late fights.** In all 15 replays the winner was ahead
   from about tick 21. Median at t100 Scourge 497 vs Atom 1227 (Atom losses) and 505 vs 1328 (mid-field losses); at
   t200 794 vs 2418. In 10 of 15 losses at least 70% of the final margin already existed at t200. Scourge reaches pop
   128 at t36-44 and 512 at t81-175; AtomPush/AtomCrasher/Noob+/Noob++/Aegis reach 128 at t28-33 and 512 at t56-82.
   Early births (t < 200): Scourge 1101 per game vs AtomPush 2747, AtomCrasher 1911; 28% of Scourge's children
   have energy >= 8 (AtomPush 3%, AtomCrasher 11%), i.e. Scourge cells wait for e >= 16 instead of splitting at 5.
   Likely cause (suspected, not measured directly): the prey rule, "5 <= e < 16 with an enemy anywhere in the 5x5:
   rest until tick 2980", which halts splitting along every contact zone from the first contact (first Scourge cell
   killed by the winner at t30-111 in 12 of 15).
3. **After t200 the front is a treadmill Scourge holds: the refill works.** The winner ate 107,342 Scourge cells over
   the 15 games; Scourge refilled 98% of those squares itself (t < 500: 12,661 of 13,058; t >= 1000: 73,329 of
   74,917). Scourge's own kills of the winner are tiny (2,059 in total, Atom fronts are fed fat), so it never gains land
   back: Scourge's pop changes by -66 to +63 from t500 to the end in 9 of 15 games. Late land loss happened in 6 of 15
   (-274 to -525 from t500), by losing a few % of contested refills (AtomCrasher 103514 8%, 103661 6%, rooby
   103716 6%, 103722 14%, AtomPush 103570 5%; in 103237 the winner took only 0.6%, so the loss there went to the
   third colony); against AtomPush it is usually 0.0-0.1% after t500. Only 4 of 15
   losses (103589, 103661, 103716, 103722) got more than half their margin after t200.
4. **Mid-field losses are mostly not fights at all.** In 103701 (Noob+), 103502 (Noob++) and 103548 (Aegis) the winner
   killed only 6-48 Scourge cells: it simply took the empty land faster and Scourge was boxed in (103701: Scourge stuck
   at 478 from t261). Against rooby (103716, 103722) and AtomCrasher it is the slow refill-race drain of finding 3.

## Tables

Pops Scourge / winner (S/W); "S < 90%" = first tick Scourge is below 90% of its peak; "W passes" = first tick > 20
with the winner larger.

| Match | Winner | t50 | t100 | t200 | t500 | t1000 | end | S peak (tick) | S < 90% | W passes |
|---|---|---|---|---|---|---|---|---|---|---|
| 103128 | AtomPush | 233/392 | 497/1316 | 644/2675 | 650/2903 | 657/2934 | 654/2957 | 658 (805) | - | 21 |
| 103208 | AtomCrasher | 166/332 | 451/1134 | 794/2418 | 1032/3061 | 1039/3055 | 1036/3055 | 1039 (814) | - | 21 |
| 103237 | AtomPush | 152/296 | 362/796 | 831/2106 | 1023/2197 | 1019/2111 | 731/2113 | 1043 (691) | 1525 | 21 |
| 103446 | Covetous | 222/236 | 523/658 | 1247/1375 | 1644/1831 | 1650/1825 | 1649/1825 | 1652 (789) | - | 26 |
| 103502 | Noob++ | 166/405 | 518/1505 | 785/2768 | 889/3068 | 902/3194 | 935/3161 | 935 (2972) | - | 21 |
| 103514 | AtomCrasher | 198/335 | 464/1332 | 522/2626 | 614/3223 | 607/3486 | 300/3793 | 652 (733) | 1127 | 21 |
| 103548 | Aegis | 178/389 | 503/1328 | 961/2608 | 1109/2964 | 1165/2910 | 1172/2907 | 1172 (2817) | - | 21 |
| 103570 | AtomPush | 220/375 | 618/1351 | 779/3062 | 741/3352 | 688/3405 | 467/3625 | 784 (165) | 841 | 21 |
| 103589 | AtomCrasher | 153/263 | 338/665 | 366/1335 | 330/2036 | 259/3184 | 264/3819 | 370 (170) | 495 | 21 |
| 103642 | AtomPush | 228/405 | 726/1461 | 1649/2264 | 1869/2221 | 1869/2221 | 1872/2220 | 1875 (2059) | - | 21 |
| 103661 | AtomCrasher | 222/293 | 615/857 | 1263/2145 | 1381/2713 | 1311/2783 | 1010/3085 | 1407 (274) | 1260 | 21 |
| 103693 | AtomPush | 198/387 | 518/1227 | 828/2652 | 917/3175 | 911/3175 | 918/3175 | 920 (404) | - | 21 |
| 103701 | Noob+ | 249/415 | 437/1373 | 475/2810 | 478/2947 | 478/2964 | 478/2994 | 478 (261) | - | 21 |
| 103716 | rooby | 221/211 | 568/761 | 762/2272 | 678/3416 | 593/3498 | 354/3739 | 769 (208) | 432 | 58 |
| 103722 | rooby | 196/211 | 505/681 | 594/1388 | 525/1817 | 427/1938 | 0/2399 | 600 (159) | 398 | 30 |

Fights Scourge vs the winner, all 15 pooled (S-by-W: Scourge cells the winner ate to death; refilled by whom):

| Window | S-by-W | refilled by S / W | W-by-S | refilled by S / W | contested squares won S / W |
|---|---|---|---|---|---|
| t < 500 | 13,058 | 12,661 / 392 | 1,267 | 1,008 / 258 | 13,693 / 653 |
| 500-1000 | 19,367 | 18,998 / 366 | 428 | 164 / 264 | 19,188 / 641 |
| >= 1000 | 74,917 | 73,329 / 1,550 | 364 | 92 / 270 | 73,534 / 1,846 |

Per-opponent (100 games; Scourge wins / games with that opponent present; first-games table = the 50 games before
05:18 local):

| Opponent | now | first games | opponent won |
|---|---|---|---|
| AtomPush | 7/12 | 3/8 | 5 |
| AtomCrasher | 11/16 | 1/1 | 4 |
| Covetous | 12/19 | 5/10 | 5 |
| Brawler v2 | 7/12 | 6/7 | 2 |
| Brawler | 10/14 | 5/9 | 1 |
| Bouncer | 6/7 | 5/6 | 0 |
| Sprint | 11/12 | 5/7 | 0 |
| rooby | 15/18 | - | 2 |
| Noob+ | 13/17 | - | 2 |
| Noob++ | 7/10 | - | 2 |
| Aegis | 6/10 | - | 2 |
| Contagion | 0/2 | - | 1 |

The rest (Hunter, Medic, Random, zergling, gemAlert_v3/v4, squirtle, choochoo, Walker, Noob, Bulwark) never won;
Scourge's losses in their games went to the fourth colony. Full tables: `tools/pull3/tab.py` output.

## Design implications (one bet each)

1. **Grow like an Atom until the fronts set (biggest lever).** Bet: removing or narrowing the prey rule during the
   land grab (e.g. split at e >= 5 regardless of enemies before ~t300, or hold only when an enemy is orthogonally
   adjacent to the target square, not anywhere in the 5x5) raises Scourge's t200 pop from ~800 toward ~1500 and
   flips the mid-field losses (Noob+/Noob++/Aegis/rooby) and some Atom losses. The cost the rule guards against (thin
   children eaten) is already covered: Scourge refills 97% of eaten squares even before t500.
2. **Spread the split directions.** Bet: replacing the fixed DOWN, RIGHT, UP, LEFT split order with a per-cell
   varied order (e.g. from cell parity or the free-square count) shortens Scourge's time to pop 512 (t81-175 now vs
   t56-82 for the Atoms, whose splits "spread out"). Check first in the replays: Scourge's frontier length vs pop at
   t20-80.
3. **Keep the refill gate; patch only its late leaks.** Bet: the late drain (5-14% of contested squares lost to
   AtomCrasher, rooby and once AtomPush, -270 to -525 cells in 6 of 15 losses) comes from freed squares the gate does not see
   (squares 2 and 22, beyond UP/DOWN) or children below R; reading those two squares would remove most of it. Worth
   about 300 cells in a third of losses, so it decides few games; do it only if it is cheap in instructions.
4. **Don't spend instructions on biting back.** Bet: an attack mode would not pay: Scourge ate the winner's cells to
   death only 2,059 times vs 107,342 the other way, because Atom fronts are fed to the cap; land after t200 is held by
   refills, not won by bites.

## What this says about the simulator's late game

The real late game between a refilling cell and an Atom is a stable treadmill: about 3-8 front deaths per tick,
98-100% refilled by the defender, net land change near 0 after t500, with slow drains only where the attacker wins
5-14% of contested refills. So late land is set by the per-pair contested-refill share, which the sim must match.
The sim's known fault (thin pumps keeping land after t500) means it gives non-refilling defenders a refill share
near Scourge's; real thin pumps lose far more. Calibration targets from this pull: contested-refill share per pair
and window (table above; per-game values in `losses.py`), front deaths per tick, and the defender's pop change from
t500 to the end (Scourge: within +-6% in 8 of 15 losses, -20% to -100% in the other 7). The early grab matters more for winning:
the sim should also be checked on time-to-pop-128/512 per cell (Scourge 36-44 / 81-175, Atoms 29-33 / 56-82).

## Limits

Only losses were downloaded (no wins to compare Scourge's early growth when it wins). "Prey rule causes the slow
grab" is inferred from child energies and the cell's rules, not measured from hold events. 15 replays, chosen
(9 of the 9 Atom losses, 5 mid-field, 1 Covetous), not random.
