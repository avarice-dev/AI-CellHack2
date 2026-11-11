# Brief: why do our cells stall at contact, and how do the new cells break fronts?

Self-contained. Read this file; open other files only if a specific number is needed (paths given).
Do not visit the site, put anything on the ladder or run long jobs. Thinking only. Answer compactly.

## The game (CellHack2, ruleset v9; full text: docs/Rules _ CellHack2.pdf, 3 pages)
- 64x64 grid, 4 colonies, 1 start cell each (energy 10, random square), 3000 ticks. Rank: population, then
  total energy, then fewer total instructions. Ladder points 3/2/1/0.
- Each tick: (1) **Decide**: every cell's x86 function sees a snapshot (5x5 view, its own 64 bytes of memory) and
  returns one action; the engine counts the instructions it ran (every one incl. taken jumps and ret).
  (2) **Act**: all cells of all colonies in ONE pass, fewest instructions THIS CALL first; ties random by seed.
  Each action sees the board as the earlier turns left it.
- REST +1 (the only income; nothing at the cap). EAT: takes up to 2 from the orthogonal neighbour, adds to the
  eater; **the bitten cell is stunned: if it has not had its turn yet, it loses its action this tick**.
  FEED: gives 2 (or all) to the neighbour (friend or enemy). SPLIT: child in an empty neighbour square with
  half the energy (child floor(e/2)), needs e >= 5. MOVE into an empty square.
- A cell at 0 dies on the spot (no turn, cannot be eaten or fed, keeps its square to the end of the tick).
  A square freed by a death opens NEXT tick; one freed by a move opens the same tick. No swaps.
- Tidy: cap 50 (applied at end of tick, so mid-tick values can exceed 50). Newborns act next tick.
- Limit 1000 instructions per call (fault = no action). No diagonal eats. Matches are deterministic per seed.

## Our cells (generated asm, cells/gen_*.py)
- Shared kernel: **F5 bite**: if any orthogonal enemy, EAT in 5 instructions (any direction; table picks the
  target). Always bites when an enemy is adjacent, even when capped (a capped eater gains nothing).
- **Refill** (11): empty orthogonal square an enemy could reach next tick -> split into it (child >= 6).
- Split 13-16 (fixed order D, R, U, L). Feed: capped donors (e >= 47) feed the poorest friend at margin >= 2;
  never feed a target >= 47. Schism adds: no enemy in 5x5, boxed in, e >= 6 -> feed a friend that has an empty
  neighbour (feed path 32-86). Rest path 17-50.
- **Schism** (ladder, 2379 games): avg 77 instructions per call, max 86. **Pestilence** (1025 games): Schism +
  refill by MOVE at e >= 20 (13), every other path +2; avg 79, max 88.

## Known rivals (older data, pulls 1-5, 148 replays; designs.md section 1, 10, 11.3)
- Atoms (AtomPush, AtomCrasher, HammerSpb): bite ~4 in ONE fixed direction, ~6 in a second, >= 8 in the others;
  fat interiors (87-89% of untouched cells at the cap), no moves, splits spread out, fast refills with 5-7
  children; avg 35 instructions per call, max 47. They grew 25-30% faster to t200 (pop at t20: Atom 57 vs ours 40;
  feeds per cell-tick in t0-75: Atom 36%, ours ~21%; Schism raised ours).
- Our contact study vs Atoms (replays, t75-t200): we act before them in 73-90% of front ticks; bite rate ours 66%
  of front ticks vs 61%; front energy 33 vs 30; feeds to front similar; we focus fire more; we retake 96-97% of our
  own freed squares (Atom 81-86%). **Yet the line still stalls where it formed**, and the gap stays.
- What our studies never measured: attackers per victim at each death, whether the victim's feeder acted that
  tick, the shape of the front at kills, or who takes a death-freed square across colonies.

## New data (2026-11-10; data/cogbloom-pages-2026-11-10.md)
Leaderboard (ratings dropped across the field): Schism 1432 (77 insns/call), Pestilence 1428 (79), **CogBloomXT
1424, 27 wins of 31, avg place 1.13 (47)**, ClaudeHunter 1311 (19), AtomPush 1298 (35), AtomCrasher 1295 (35),
NomNom2 1250 (44), Ironbloom 1239 (48). CogBloomXT and Ironbloom are by one author (Yen).

| Match | Result | E/cell at end | Insns avg (max) |
|---|---|---|---|
| 123990 | Ironbloom 2967 cells (1st), Schism 1105 (2nd) | 49.7 vs 45.8 | 44 (189) vs 72 (86) |
| 123880 | CogBloomXT 4095 of 4096 squares; AtomCrasher dead (peak 466) | 49.9 | 45 (193) vs 31 (47) |
| 123941 | CogBloomXT 3755; AtomCrasher dead (peak 847) | 49.9 | 46 (195) |
| 123934 | CogBloomXT 2520, AtomCrasher 657 (peak 944) | 49.7 | 49 (191) |
| 123888 | AtomPush 2745 beat CogBloomXT 1345 (peak 1627) | 50.0 | 46 (191) |

Yen's cells: whole colony at about 50 energy, peak = final when they win (they never lose ground), max path
189-195 (much longer than ours), and they **eliminate AtomCrasher**, which we only ever hold even with.

## What I am confused about (the questions)
1. **The stalemate arithmetic.** On a straight front each enemy front cell touches one of ours: one bite = -2,
   one feeder behind = +2, so net 0 whoever is faster. Speed decides only who is stunned. Is that the full
   reason fed fronts freeze, or am I missing a rule effect (stun on feeders? death mid-tick before the feed
   lands? the cap applied only at Tidy?)
2. **How do Yen's cells kill a fed Atom front?** Candidates: (a) two or three attackers on one victim (corners,
   staircase or concave fronts), maybe shaped on purpose; (b) a low victim finished by a second fast bite
   before its feeder's turn (death on the spot); (c) starving the feed chain; (d) fast fat refills (child 25 from
   a 50) so every kill turns into held ground; (e) something in the 189-195 path (a rare long plan: reading the
   5x5 to pick targets or coordinate through shared view state). Which fits the evidence best, and why?
3. **Why is their whole colony at 50 and still winning?** A capped cell earns nothing. Does a capped colony
   mean they stop splitting the interior and spend everything at the front?
4. **Was "instruction count" ever the right lens?** The user's observation: rivals at 30-50 average beat our
   77-79. My current view: the average does not set turn order (each call's own count does), and against the
   Atoms we bit first and still stalled. Is there a mechanism by which the average (the common paths) does
   matter, e.g. feeders or splitters near the front acting late in the tick?
5. **Our design errors.** Our front cell always bites, even capped (gains 0). Would a capped front cell do better
   feeding a neighbour, splitting into a diagonal-opening, or holding for a coordinated kill? Is "every front cell
   bites the poorest neighbour" the thing that keeps us at one attacker per victim?

## What I want back (short)
- The most likely mechanism for 2 (ranked, with the reasoning from the rules).
- For each, the one measurement in a replay that would confirm or kill it. Available: replay 123880
  (CogBloomXT wipes out AtomCrasher) and 123990 (Ironbloom beats Schism); our decoder gives per-tick events
  in turn order (actor, action, target, energies) and board snapshots.
- What Bane (our next combat cell) should do differently at contact, in a few lines, assuming the top
  mechanism is right. Instruction-cost estimates welcome (F5 bite = 5 is our floor so far).
