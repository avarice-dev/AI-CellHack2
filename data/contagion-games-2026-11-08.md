# Contagion: how it does and why (pull 4, 2026-11-08)

Data: all 95 finished ladder games of Contagion (cell 157; matches 103614-104195, fewer than 100 exist),
`data/pull4/matches-contagion-2026-11-08.json`, from the rjclay ladder match list (player id 21, pages 1-10, filtered
for Contagion) plus one match page per game. 12 replays decoded offline (6 wins, 6 losses; `data/pull4/replays/`,
git-ignored, 282 MB; decoder `tools/pull2/mine.py` with `CH_PULL=pull4`; 0 keyframe mismatches, 0 count mismatches in
all 12; outputs `data/pull4/mining/`). Tables: `python -I tools/pull4/tab.py` and `python -I tools/pull4/games.py`.
Pull 3 numbers (Scourge, 15 losses) are from `data/scourge-losses-2026-11-08.md`.

## Findings

1. **Overall: 70 of 95 won (74%), places 70/22/3/0, never 4th: the same record as Scourge in pull 3 (74/100,
   74/23/3/0).** Rating 1000 -> peak 1608 (after match 104006) -> 1542 now. By thirds: 25/31, 25/31, then 20/33 (61%)
   in the newest third, the same late drop Scourge showed after its peak. Losses: Brawler 6, AtomPush 4, Bouncer 3,
   Scourge 3, AtomCrasher 3, rooby 2, Covetous 2, Brawler v2 1, Noob+ 1. Brawler is Contagion's worst opponent
   (16/22, 6 losses), while it beat Scourge only once in pull 3.
2. **Contagion vs Scourge: Contagion placed higher in 10 of the 13 games they shared** (Scourge won 103756, 103827,
   104078). In the 7 decoded shared games they barely fight (C-by-S 5-311 cells per game, almost all refilled); the
   result is who got more land, and early speed between the two did not predict it: Contagion reached 512 first in 5
   of 7 but won only 3 of those 5, and won 103943 while 26 ticks slower to 512.
3. **Early growth: Contagion is faster than Scourge, but modestly.** Medians over the 12 replays: pop 128 at t33
   (range 32-43), 512 at t74.5 (61-109), pop t100 754, t200 1438. Scourge in the same 7 games: 128 at t36 (35-38),
   512 at t83 (73-91), t100 674, t200 1206. Early births (t < 200) 1531 per replay vs Scourge 1344 (AtomPush 1560,
   AtomCrasher 1439). Pull 3's slower Scourge numbers (128 at t36-44, 512 at t81-175, t100 ~500) came only from
   Scourge's losses, where the fast rivals made contact early; in these games Scourge grows almost as fast as
   Contagion. So part of pull 3's "slow Scourge" was the opponent, not the kernel alone.
4. **Contagion wins the pre-contact grab and loses the contact phase (t75-t200).** In its 6 losses Contagion is
   ahead or level at t50 (median 281 vs winner 256) and reaches 512 as fast as the winner (t74 vs t72), but at t100
   it is already behind (664 vs 952) and at t200 far behind (1130 vs 1930): from t100 to t200 Contagion adds a median
   414 cells, the winner 957. The first Contagion cell killed by the winner dies at t70-120 in all 6 losses, i.e. the
   gap opens exactly when contact starts. In its wins the runner-up is the slow one (512 at t85, t200 1081 vs
   Contagion 1830). Scourge in pull 3 was behind already at t50 (median ~198 vs ~335), so the grab assist did fix
   the pre-contact part.
5. **Contagion's early children are mostly cheap, and fewer are fat than in Scourge's pull 3 losses.** 57% of Contagion's children before
   t200 have energy 2 and 14% have e >= 8 (Scourge in these games 77% and 14%; pull 3 Scourge losses 28% >= 8);
   Contagion has a large extra hump at e = 6-7 (2,748 of 18,373 children) that Scourge lacks (708 of 9,411). Scouts
   are barely used: 6 moves per replay.
6. **After t200 the refill treadmill holds, as for Scourge.** Contagion refilled 96-97% of the squares its rival ate
   in every window (wins: 19,375 of 20,195 eaten; losses: 15,283 of 15,914). Late land loss (t500 -> end) above 200
   cells only in 104099 (-316, AtomPush), 104141 (-205, Brawler) and 104068 (-325, AtomCrasher); the other 9 are
   within +-25. Losses are decided by t200, not by late fights: AtomPush 104018 ate 4,507 Contagion cells but took
   only 31 of those squares.

**Key question answered.** Contagion does grow faster early than Scourge (pull 3 numbers by a lot, same-game numbers
by 3 ticks to 128 and ~9 to 512), and that is part of why it beats Scourge's record against the field slightly
(rating 1540-1600 vs Scourge 1490-1650), but it is not what decides its losses: against Atoms and Brawler it matches
their pre-contact speed and then falls behind once contact starts, while it still runs the same prey hold
(5 <= e < 16 with an enemy in the 5x5: rest). That **supports the early-split bet** (drop the prey hold early) and
sharpens it: the hold should be dropped through the contact phase, at least to t ~200, not only before first
contact; faster isolated growth alone (what grab assist bought) has already been captured and did not change the
loss pattern. Not measured directly: how many Contagion cells actually sat in the prey hold during t75-200 (the
decoder does not log rest decisions); a box-in by a third colony would look similar in the pop curves.

## Tables

Pops Contagion / Scourge / X (X = runner-up in wins, winner in losses; "-" = Scourge absent).

| Match | Result | X | S place | t50 | t100 | t200 | t500 | t1000 | end | C t500->end |
|---|---|---|---|---|---|---|---|---|---|---|
| 103943 | win | Scourge | 2 | 162/240 | 466/674 | 980/1302 | 2107/1988 | 2106/1990 | 2105/1991 | -2 |
| 103972 | win | Scourge | 2 | 296/206 | 778/632 | 1498/1206 | 1650/1221 | 1657/1242 | 1674/1258 | +24 |
| 104030 | win | Scourge | 2 | 343/244 | 1049/808 | 1928/1199 | 2434/1662 | 2439/1657 | 2438/1658 | +4 |
| 104149 | win | Scourge | 2 | 230/228 | 763/576 | 2144/774 | 2493/1006 | 2500/1573 | 2498/1598 | +5 |
| 104099 | win | AtomPush | - | 279/234 | 745/507 | 1731/883 | 2645/1054 | 2576/1121 | 2329/1364 | -316 |
| 104141 | win | Brawler | - | 360/262 | 1152/596 | 1964/964 | 2078/1033 | 2029/1082 | 1873/1206 | -205 |
| 103756 | 2nd | Scourge | 1 | 242/247 | 834/930 | 1674/1724 | 1933/2162 | 1935/2161 | 1943/2153 | +10 |
| 103827 | 2nd | Scourge | 1 | 322/232 | 612/679 | 771/1987 | 872/2917 | 891/3205 | 868/3228 | -4 |
| 104078 | 2nd | Scourge | 1 | 299/250 | 668/668 | 1296/1067 | 1687/1838 | 1703/2393 | 1706/2390 | +19 |
| 104018 | 2nd | AtomPush | - | 279/404 | 855/1320 | 1378/2336 | 1586/2483 | 1586/2485 | 1577/2493 | -9 |
| 104068 | 2nd | AtomCrasher | - | 277/332 | 634/1192 | 810/2492 | 1058/3018 | 1012/3081 | 733/3357 | -325 |
| 104091 | 2nd | Brawler | - | 284/262 | 660/974 | 965/1872 | 985/2155 | 985/2458 | 987/3073 | +2 |

(Where X is Scourge, the second number is Scourge's pop.)

Growth: first tick at pop 32 / 128 / 512.

| Match | Result | Contagion | Scourge | X | first C cell killed by X |
|---|---|---|---|---|---|
| 103943 | win | 19 / 43 / 109 | 16 / 36 / 83 | Scourge | 89 |
| 103972 | win | 18 / 33 / 74 | 16 / 38 / 87 | Scourge | 146 |
| 104030 | win | 18 / 32 / 63 | 16 / 36 / 73 | Scourge | 97 |
| 104149 | win | 16 / 37 / 80 | 16 / 37 / 91 | Scourge | 56 |
| 104099 | win | 16 / 33 / 76 | - | AtomPush 15 / 33 / 103 | 52 |
| 104141 | win | 18 / 32 / 61 | - | Brawler 18 / 36 / 82 | 147 |
| 103756 | 2nd | 17 / 36 / 75 | 16 / 36 / 74 | Scourge | 120 |
| 103827 | 2nd | 18 / 32 / 73 | 16 / 36 / 83 | Scourge | 70 |
| 104078 | 2nd | 18 / 33 / 76 | 16 / 35 / 78 | Scourge | 79 |
| 104018 | 2nd | 16 / 33 / 71 | - | AtomPush 15 / 29 / 57 | 101 |
| 104068 | 2nd | 18 / 33 / 80 | - | AtomCrasher 16 / 32 / 62 | 92 |
| 104091 | 2nd | 19 / 34 / 73 | - | Brawler 18 / 36 / 70 | 87 |

Medians (ticks to 128 / 512; pop t100 / t200):

| Group | n | to 128 | to 512 | t100 | t200 |
|---|---|---|---|---|---|
| Contagion, all | 12 | 33 | 74.5 | 754 | 1438 |
| Contagion, wins | 6 | 33 | 75 | 771 | 1830 |
| Contagion, losses | 6 | 33 | 74 | 664 | 1131 |
| Scourge, same games | 7 | 36 | 83 | 674 | 1206 |
| Winner in C's losses | 6 | 35.5 | 72 | 952 | 1930 |
| Runner-up in C's wins | 6 | 36 | 85 | 614 | 1082 |
| Scourge in its pull 3 losses | 15 | 36-44 | 81-175 | ~500 | ~794 |
| Pull 3 winners (Atoms etc.) | 15 | 28-33 | 56-82 | ~1250 | ~2418 |

Fights Contagion vs X, pooled (C-by-X: Contagion cells X ate to death, refilled by C / X):

| Games | Window | C-by-X | refilled C / X | X-by-C | refilled C / X |
|---|---|---|---|---|---|
| wins | t < 500 | 2,819 | 2,629 / 190 | 353 | 208 / 145 |
| wins | 500-1000 | 3,939 | 3,769 / 170 | 95 | 37 / 57 |
| wins | >= 1000 | 13,437 | 12,977 / 452 | 95 | 46 / 49 |
| losses | t < 500 | 1,958 | 1,842 / 115 | 150 | 92 / 58 |
| losses | 500-1000 | 2,741 | 2,648 / 93 | 50 | 29 / 21 |
| losses | >= 1000 | 11,215 | 10,793 / 415 | 249 | 119 / 130 |

Early births (t < 200) in the 12 replays:

| Colony | replays | births/replay | child e median | child e = 2 % | child e >= 8 % | moves/replay |
|---|---|---|---|---|---|---|
| Contagion | 12 | 1531 | 2 | 57 | 14 | 6 |
| Scourge | 7 | 1344 | 2 | 77 | 14 | 0 |
| AtomPush | 3 | 1560 | 3 | 43 | 9 | 0 |
| AtomCrasher | 2 | 1439 | 3 | 48 | 5 | 0 |
| Brawler | 3 | 1369 | 3 | 0 | 4 | 0 |

Per-opponent (95 games; Contagion wins / games with that opponent; opponent won): Brawler 16/22 (6), Bouncer 11/16
(3), Bulwark 10/16, Random 13/16, zergling 14/15, AtomPush 9/14 (4), Covetous 8/14 (2), Brawler v2 11/14 (1), Medic
11/13, Scourge 7/13 (3), Aegis 10/13, choochoo 12/13, Noob 7/13, gemAlert_v3 8/12, Walker 8/12, Hunter 10/11,
AtomCrasher 8/11 (3), squirtle 10/11, Noob+ 6/10 (1), gemAlert_v4 7/9, Noob++ 8/9, rooby 6/8 (2).

## Implications for the next cells (one bet each)

1. **Early-split cell (in progress on Scourge): keep it, and run the no-hold window through t ~200, not just until
   first contact.** Contagion shows the pre-contact grab is already fixable (grab assist did it); the losses now open
   at t75-200, after first contact, which is exactly where the hold acts. Check: on the ladder, pop at t200 against
   Atoms/Brawler should move from ~1130 toward ~1900.
2. **Build it on Contagion, not Scourge, if a second variant is made.** Contagion already has the faster pre-contact
   grab (t50 ahead of the eventual winner) and places above Scourge 10 of 13 times; an early-split Contagion would
   test the contact-phase fix without also re-paying for the slower opening.
3. **Measure the hold directly before tuning T.** Add a decoder stat: per colony, cells with 5 <= e < 16 that did
   not split while having an enemy in their 5x5, per tick for t < 300. If this count is small in Contagion's losses,
   the cause is box-in by a third colony and the early-split bet will not help; then the bet is direction of growth
   (expand away from the nearest enemy).
4. **Brawler is now the main problem opponent for Contagion (6 of 25 losses).** In 104091 Brawler matched Contagion's
   pace to 512 and then took the land with few kills (569 Contagion cells eaten in the whole game), so this is the
   same contact-phase loss, not a fight; the early-split cell should be checked against Brawler specifically.

## Limits

- 12 replays chosen (not random): wins with Scourge present and losses to Scourge/Atoms/Brawler. Same-game Scourge
  numbers are from 7 games only.
- Rating trend may be variance; rival versions were not re-checked.
- Prey-hold activity is inferred from timing (gap opens with first contact), not counted.
