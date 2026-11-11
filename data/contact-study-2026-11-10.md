# Contact study: how Yen's cells win (2026-11-10)

Data: pull6, replays 123880 (CogBloomXT eliminates AtomCrasher, ends t2088) and 123990 (Ironbloom 1st, Schism 2nd,
3000 ticks). Decoder clean (0 keyframe / count mismatches). Tools: `tools/replay/actions.py`, `claims.py` (new),
`bite_targets.py`, `front_feed.py`, `freed_squares.py`, `birth_order.py`. Match pages: `cogbloom-pages-2026-11-10.md`.
Two games only: the numbers are indicative.

## 1. Populations
123880 (Bouncer, CogBloomXT, AtomCrasher, BigBadWolf): t20 38/23/52/29; t50 226/355/206/156; t100 351/1016/295/283;
t200 385/2104/401/494; t500 94/3102/453/439; t1000 0/3748/327/19; t2088 0/4095/0/0.
123990 (Ironbloom, Schism, BigBadWolf, Smarter Hunter): t50 252/330/136/253; t100 711/831/391/936;
t150 1124/957/493/1240; t200 1352/972/518/1247 (board full); t500 1739/1049/602/699; t1000 2272/1086/720/14;
t3000 2967/1105/24/0.
Schism led Ironbloom until t100, then froze at ~1000 for 2900 ticks. Ironbloom took the land of the two dying
colonies (+1600); Schism took almost none. The Schism-Ironbloom front itself was even (Ironbloom lost 689 cells,
Schism 746; Schism refilled 98% of its own squares, Ironbloom 87%).

## 2. Turn order at the front (actions.py, start-of-tick enemy pattern -> action)
Schism cells facing Ironbloom (t150+): enemy at U: bitten first 96%; UR: 99%; L: eat 52% / bitten first 48%;
DL, UL: 52/48; R: eat 100%. So Ironbloom's bite is faster than our 5 downward (<= 4), equal (5, coin flip) right
and up, slower left. Ironbloom cells: bitten first 0-8% in three directions, 25-58% where our bite ties.
CogBloomXT vs AtomCrasher: AtomCrasher bitten first 75-94%; CogBloomXT 1-16% (100% only at UL, Atom's fast side).
Against the Atoms (old study) we acted first in 73-90% of front ticks; against these cells about half the time.
A stunned cell cannot bite, split or refill that tick.
Split-path order (birth_order.py, t >= 75): Schism's births come before every other colony's (pre 100%);
CogBloomXT's come after AtomCrasher's and Bouncer's (post 100%). Refill turn order is not their edge.

## 3. Freed squares (claims.py: cells adjacent to a square freed by a death, what they did next tick)
| Colony, squares of | sq | filled by self | by owner | candidates with an enemy nbr | bitten first | child E |
|---|---|---|---|---|---|---|
| Ironbloom, enemy (t150+) | 2546 | 68% | 20% | 59% | 4% | 19.1 |
| Schism, enemy (t150+) | 430 | 34% | 54% | 79% | 18% | 10.5 |
| Ironbloom, enemy (t100-200) | 193 | 76% | 23% | 52% | 1% | 15.4 |
| Schism, enemy (t100-200) | 87 | 43% | 47% | 71% | 4% | 7.8 |
| CogBloomXT, enemy (123880) | 7311 | 31% | 64% | 57% | 7% | 14.6 |
| AtomCrasher, own (123880) | 4412 | 89% | - | 33% | 5% | 6.1 |
Both Ironbloom and Schism behave the same way: a candidate with an enemy neighbour bites (87% / 71%), one without
splits into the square (96% / 90%). The gap is in opportunities (2546 vs 430 adjacent enemy squares: Ironbloom
bordered the dying colonies), in how often our candidate is stunned (18-23% vs 4-7%), and in child energy
(ours half theirs). CogBloomXT's free candidates often do nothing (51% none): it refills enemy squares selectively.

## 4. How CogBloomXT kills an Atom
AtomCrasher was held to ~400 cells by CogBloomXT's opening (t50 355 vs 206, t100 1016 vs 295). From t400 its front
(22 cells) sat at 7.5 energy: every refill was a 6-energy child, bitten first 75-94% of ticks, dead in ~3 ticks
(2.2 front deaths per tick). CogBloomXT took 31% of the freed squares, so the Atom lost about 0.2 squares a tick
for 1700 ticks. No focus fire (focus share 7.7%, like ours), no special targeting (it bit the richer neighbour 73%).
Our old data vs Atoms shows an even front (front energy 30 vs 33, similar death rates): the Atom's front never
got thin against us because we were not ahead enough to stun it and starve its refills.

## 5. Feeding and front energy (front_feed.py)
| Cell | front cells | front E | inner E | feeds to front /t | front deaths /t |
|---|---|---|---|---|---|
| Ironbloom | 71 | 41.5 | 49.4 | 8.4 | 0.24 |
| Schism | 74 | 33.8 | 45.5 | 33.8 | 0.30 |
| CogBloomXT | 47 | 40.0 | 49.3 | 7.3 | 1.14 |
| AtomCrasher | 22 | 7.5 | 37.1 | 13.7 | 2.17 |
Schism feeds its front 4x more than Ironbloom and still holds it 8 energy lower; Schism's interior feeds 411 times a
tick (Ironbloom 4). Their colony sits at the cap and barely feeds; ours churns energy. Their front holds anyway
because it is rarely stunned and its refills are fat.

## 5b. Bane v1 vs CogBloomXT, replay 124335 (the two other colonies died by t10: a 1v1 land grab)
Populations Bane / CogBloomXT: t30 122/104, t40 206/235, t50 305/462, t60 408/707, t75 584/1082, t100 753/1486,
t200 1251/2570, t250 1338/2758, then not one square changed hands to t3000 (final 1331/2765).
Opening (`early_growth.py --min=1`, per cell-tick): CogBloomXT splits 13.6% / feeds 0% / moves 7.8% / rests 79% in
t0-30, splits 6.0% / rests 92% in t30-60, 1.9% / 95% in t60-100; Bane 10.3% / 9% / 0% / 81%, then 3.9% / 17%,
1.7% / 28%; after t100 Bane feeds in 49% of cell-ticks, CogBloomXT in 0.7%.
`opening.py`: CogBloomXT's 45 moves (t1-31) are scouts: from the founder at (57,15) a 5-energy cell walked LEFT 15
squares to (41,15) and a 2-energy child walked DOWN 15 squares to (57,31); at t17 the new blob at (41,15) sent a
2-energy scout DOWN 15 squares to (41,31). All moves outward in straight lines toward the board centre; splits
from exactly 5 (236 of 240 parents); no holds. Same pattern in 123880 (53 moves: 15 at energy 5, 38 at 2).
So by t30 it grows as 3-4 separate blobs, each with a full perimeter. Our single blob's perimeter grows with the
square root of its area; feeding energy to that edge cannot make up for three missing perimeters.

## 6. What this says
1. The new cells bite as fast as F5 or faster in one direction. Our bite is at the SSE floor (load, compare, mask,
   action, exit = 5), so the front against them is a coin flip at best: a stalemate, not a loss.
2. The games are lost on the rest of the board: the last land grab (t100-200: Ironbloom +640, Schism +140) and the
   land of weak colonies (Ironbloom 1731 enemy squares taken, Schism 146). A cell of ours with an enemy neighbour
   never splits; stunned cells do nothing; our refill children are half theirs.
3. Instruction averages (ours 72-79, theirs 44-49) are a symptom: our interior runs the 32-86 feed paths constantly
   (411 interior feeds per tick) for a front that is still thinner than theirs.
4. Against Atoms, being ahead at t100 is what starts the grind; the grind itself is ordinary biting.
Not measured: how Yen's cells choose between rest and refill (51% none), what their 189-195-instruction path does,
and whether their opening is better than Schism's (Schism led until t100 in 123990).
