# Siect-F opening growth, 10 ladder games (2026-11-13)

Decoded in the browser from the site's replays: cells at t10..t100 and the start area (Voronoi, Manhattan, squares nearer this start than any other). The board is 64x64, so the average area is 1024.

| match | Siect-F area | t10 | t20 | t30 | t40 | t50 | t60 | t70 | t80 | t90 | t100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 147122 | 787 | 6 | 27 | 123 | 406 | 800 | 1246 | 1677 | 1998 | 2234 | 2364 |
| 147113 | 1022 | 7 | 31 | 143 | 414 | 800 | 1199 | 1500 | 1745 | 1889 | 1971 |
| 147103 | 1512 | 7 | 32 | 152 | 418 | 732 | 1062 | 1351 | 1619 | 1856 | 2040 |
| 147092 | 1113 | 7 | 31 | 136 | 381 | 809 | 1340 | 1970 | 2393 | 2640 | 2771 |
| 147080 | 659 | 6 | 27 | 119 | 355 | 628 | 947 | 1304 | 1586 | 1789 | 1911 |
| 147068 | 1465 | 7 | 31 | 141 | 417 | 828 | 1132 | 1322 | 1488 | 1575 | 1620 |
| 147059 | 729 | 6 | 27 | 121 | 358 | 590 | 792 | 889 | 944 | 1001 | 1048 |
| 147047 | 1878 | 7 | 31 | 138 | 393 | 847 | 1432 | 2018 | 2394 | 2597 | 2697 |
| 147037 | 987 | 7 | 27 | 121 | 348 | 678 | 1066 | 1426 | 1636 | 1779 | 1875 |
| 147024 | 1633 | 7 | 31 | 142 | 427 | 907 | 1483 | 2054 | 2426 | 2605 | 2730 |

For comparison:
- Misfortune SOLO, local engine, empty board (sim/out/misfortune-solo-curve-2026-11-13.txt), center start: 7, 33, 136, 420, 918, 1654, 2537 at t10..t70. Corner start: 8, 40, 143, 285, 500, 757.
- Misfortune REAL, ladder 146477, area 674: 152 at t30, 513 at t60, 744 at t100. Siect-F in the same game, area 1161: 131, 1125, 2266.
- AtomVirus in 147068, area 526: 2203 at t100, ahead of Siect-F's 1620.

## Refill race (who takes a freed square, and after how many ticks)

The tool is window.refill in the browser (same decoder as above, up to t1000; t3000 for 146477). Bins are 1 / 2 / 3 / 4-5 / 6+ ticks after the death. A square is empty from the tick after the death, because a corpse holds its square until Tidy.

| match | squares Siect-F killed: refilled by Siect-F | by others | Siect-F cells killed: refilled by Siect-F | by others |
|---|---|---|---|---|
| 147122 | 1573 / 24 / 7 / 31 / 29 | 306 / 59 / 10 / 6 / 4 | 13 / 24 / 4 / 0 / 0 | 16 / 6 / 1 / 1 / 0 |
| 147113 | 2221 / 11 / 8 / 2 / 5 | 903 / 167 / 43 / 19 / 3 | 7 / 6 / 0 / 0 / 0 | 14 / 6 / 0 / 2 / 1 |
| 146477 (vs Misfortune, t3000) | 1014 / 13 / 4 / 9 / 2 | 725 / 41 / 7 / 1 / 2 | 182 / 37 / 4 / 3 / 5 | 162 / 17 / 4 / 4 / 2 |

Reading:
- Siect-F refills its kills on the very next tick (tick + 1), the earliest the rules allow. It does this for 77-70% of its kills.
- Against Misfortune, the tick + 1 race over Siect-F's dead cells is about even (182 vs 162), so the race is decided by turn order. Siect-F's refill costs about the same as our 15-instruction refill.
- In 146477 Misfortune's final population (787) is about its own start area (674): it took no one else's ground. Siect-F's 3309 is about its area (1161) plus Aegis's and garlic's.

## Misfortune vs Siect-F, all 6 shared games (start area; cells at t30 / t60 / t100 / t300 / t1000 / final)

| match | result | Misfortune area | Misfortune | Siect-F area | Siect-F |
|---|---|---|---|---|---|
| 147688 | WIN | 1481 | 140 / 891 / 2258 / 2460 / 2582 / 2698 | 496 | 120 / 645 / 811 / 917 / 843 / 787 |
| 147456 | WIN | 1296 | 156 / 967 / 1606 / 2068 / 2162 / 2526 | 831 | 116 / 1125 / 1643 / 1878 / 1932 / 1569 |
| 147569 | loss | 765 | 161 / 711 / 1125 / 1287 / 1337 / 1338 | 777 | 116 / 960 / 1835 / 2466 / 2759 / 2758 |
| 148012 | loss | 666 | 123 / 655 / 1103 / 1379 / 1557 / 1776 | 998 | 109 / 974 / 1937 / 2211 / 2535 / 2320 |
| 146477 | loss | 674 | 152 / 513 / 744 / 787 / 787 / 787 | 1161 | 131 / 1125 / 2266 / 3072 / 3309 / 3309 |
| 146773 | loss | 677 | (not decoded) | 1348 | |

Reading:
- Misfortune won both games where it started with more room (1.6x and 3x Siect-F's area). It lost all 4 where it had equal or less.
- In the equal-start game (147569, 765 vs 777), Misfortune led at t30 (161 vs 116). Siect-F then grew 1.35x faster to t60 and 1.6x faster to t100.
- So start area decides the lopsided games, but at an equal start Siect-F still out-grows us after first contact. That contact-growth gap is real.
- In 147456 Siect-F fell from 1932 at t1000 to 1569 at the end: Misfortune pushed it back late.
