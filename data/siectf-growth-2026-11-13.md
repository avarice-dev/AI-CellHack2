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
