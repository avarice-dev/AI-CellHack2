# Solo opening search (2026-11-11)

One colony alone on the board, real engine (`tools/search/opening_search.py <repo root> <set>`), mean cells over four
start squares ((30,31), (8,9), (2,60), (30,3)). The sketch policy reproduces the real cell (136 against 137 at t30).

## Set a: walk lengths, direction rule, when walkers stop, feeding

| Rule set | t20 | t30 | t40 | t50 | t60 | t75 | t100 |
|---|---|---|---|---|---|---|---|
| Bane v2.2 (real cell) | 37 | 137 | 342 | 650 | 1063 | 1794 | 2942 |
| same rule, sketch | 37 | 136 | 340 | 648 | 1057 | 1781 | 2927 |
| long walk only into open space, 8/2 | 24 | 85 | 270 | 645 | 1125 | 1961 | 3090 |
| the same, split toward the emptiest side | 23 | 81 | 262 | 651 | 1169 | 2058 | 3169 |
| first child long 8/2, emptiest side | 38 | 143 | 359 | 690 | 1115 | 1870 | 3012 |
| open-space long 6/2, emptiest side | 27 | 107 | 353 | 738 | 1215 | 2000 | 3060 |
| open-space long 12/2, emptiest side | 18 | 57 | 182 | 452 | 925 | 2002 | 3245 |
| open-space long 8/3, emptiest side | 23 | 81 | 262 | 654 | 1185 | 2078 | 3190 |
| every child walks 4 | 38 | 153 | 397 | 705 | 1093 | 1773 | 2780 |
| every child walks 3, emptiest side | 42 | 183 | 427 | 724 | 1076 | 1689 | 2615 |
| open-space long 8/2, stop when no friend in view after 2 steps | 55 | 197 | 404 | 658 | 964 | 1536 | 2460 |
| the same after 3 steps | 42 | 180 | 423 | 724 | 1116 | 1795 | 2842 |
| open-space long 16/2, stop after 4 steps with no friend in view | 37 | 147 | 409 | 736 | 1159 | 1883 | 2994 |
| first 8/2 without boxed feeding | 37 | 134 | 335 | 644 | 1048 | 1775 | 2925 |
| no long walks, 1 step | 65 | 171 | 310 | 475 | 670 | 1030 | 1734 |
| no walking | 53 | 117 | 199 | 301 | 417 | 628 | 1073 |

## Set b: fatter walkers, later splits (all worse)

| Rule set | t30 | t60 | t100 |
|---|---|---|---|
| base (first 8/2, emptiest side) | 143 | 1115 | 3012 |
| split at 6 / 8 / 10 | 78 / 37 / 21 | 881 / 512 / 279 | 2811 / 2192 / 1620 |
| long walk only from energy 10, else short | 180 | 927 | 2303 |
| wait for energy 10 (or 8), then a long walker | 92 (110) | 728 (863) | 2303 (2604) |

## Reading

- Splitting at 5 with thin walkers is right; waiting for fatter children loses everywhere.
- Boxed feeding changes nothing alone on the board.
- Every sensible variant lands within about 15% of the current cell. The best: open-space long walks with a split
  toward the emptiest side (t60 +10 to +14%, t75 +11 to +16%).
- Limits, by arithmetic: with no blocking and 2 steps per child the count grows about 17% per tick (123 at t30, 610 at
  t40): the cell follows that curve to about t40. After about 300 cells the colony cannot spread fast enough (walkers
  move 1 square per tick), so growth follows the front: about 2 * (v * (t - 24))^2 cells. v = 0.75 gives about 1450 at
  t60, v = 1 about 2600. The cell is at about 1100 to 1200 (v about 0.65). So the opening is at roughly half to
  four fifths of what the rules allow, not a quarter.
