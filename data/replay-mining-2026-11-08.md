# CellHack2 replay mining, 2026-11-08: refill race and resting income

Offline re-analysis of the 35 raw pull-2 replays (`data/pull2/replays/*.chr2.gz`; 98797 has no raw file) for two
review questions. Background and conventions: `data/ladder-data-2-2026-11-08.md`. Full tables:
`data/pull2/mining/tables.md`; machine-readable: `data/pull2/mining/refill.json`, `rest.json`, one `<id>.json` per
replay (validation, rest histograms by start energy) and `races/<id>.csv.gz` (one row per death).

## Method

- No Node.js on Windows or in WSL, so `tools/pull2/mine.py` is a pure-Python port of `CellHackViewer.decode` and
  `State.apply` from `data/pull2/site/viewer.js` (format 4, u8 energies), streamed tick by tick, one replay at a time,
  one process at below-normal priority (about 2-8 s per replay). `tools/pull2/mine_report.py` aggregates per cell name.
- **Validation:** the modelled start-of-tick state (ids, colony, x, y, energy, order) matched all 1732 keyframes in
  the 35 replays (0 mismatches), the per-tick energy count matched the modelled cell count every tick, and no birth or
  move landed on an occupied square.
- **Refill race:** each death event frees its square. The refill is the next birth or move onto that square; ticks to
  refill = refill tick - death tick; energy = the child's energy (births) or the mover's start-of-tick energy (moves).
  Contenders = colonies with a cell orthogonally adjacent to the square at the death; a race is *contested* when there
  are at least 2. Killer = colony of the last eat on the dead cell.
- **Resting income:** a cell-tick is event-free when the cell is not the eater, target, feeder, receiver, mover,
  newborn or dead in that tick. Delta = end-of-tick energy - start-of-tick energy. "Colony gain per tick" = number of
  event-free +1 cell-ticks in the window / ticks in the window, per replay, median across replays.

## Headline findings

1. **The refill race is decided in the very next tick.** No square was ever refilled in the death tick (0 cases),
   and 98-99% of AtomPush/AtomCrasher refills and 82% of Sprint's happen exactly 1 tick later; median 1 tick for
   every cell. 0.0% of death-freed squares stay empty (except a handful at match end). So it is not a speed race over
   many ticks: whoever acts on that square first in tick t+1 takes it.
2. **Sprint loses the race to HammerSpb almost every time.** In races where Sprint and the Atom colony were both
   adjacent: vs AtomPush 27339 races, Sprint won 0.5%, AtomPush 99.3%; vs AtomCrasher 6915 races, Sprint 3.6%,
   AtomCrasher 96.0%. Per match: 99239 0.3% (13958 races), 99134 0.3% (12968), 99413 2.4% (2456), 99420 1.8% (3491);
   the best for Sprint was 98983 (15.3%) and 99061 (12.9%). Sprint did best early (t0-500: 2.4% vs AtomPush, 17% vs
   AtomCrasher) and worse later.
3. **Child energy at refill: Sprint 25, Atom 6.** When Sprint does win a contested square its median child energy is
   25 (it splits at 50: 24% of all Sprint refills are exactly 25, 38% are 9-16); AtomPush and AtomCrasher refill with
   median 6 (4-8 in 71-83% of their refills). The Atom cells fill a hole with a cheap 3-6 energy child at once instead
   of waiting to be full; Sprint's refills cost far more and come later in its turn.
4. **Contested-race win share by cell (all opponents):** AtomPush 78.3%, AtomCrasher 67.1%, Brawler v2 62.6%,
   Bouncer 61.5%, Brawler 58.8%, Sprint 42.3%, Aegis 23.6%, rooby 11.6%, zergling 6.5%, Bulwark 0.0%.
5. **Atom colonies keep their own holes:** 93.8% of dead AtomPush cells and 91.4% of dead AtomCrasher cells are
   refilled by their own colony (the killer gets 6-9%); a dead Sprint cell goes 50.4% own, 49.5% to the killer.
6. **Resting income is +1 per tick for any event-free cell below 50, and 0 at 50.** Pooled over all cells, an
   event-free cell at start energy 50 never gained (35.7 M cases, 0 times +1), while at 44-49 it gained +1 in 98.1-99.6%
   of cases. For most cells the +1 share below 50 is 95-99% (Sprint 95-97%, AtomPush 95-98%, AtomCrasher 96-99%,
   Aegis 97-98%, Brawler 90-97%). This resolves pull 2's "unexplained passive +1 in 8% of idle cell-ticks": the 8%
   was diluted by cells sitting at the 50 cap. The cap is 50 for idle cells.
7. **Exceptions:** Noob 6.9%, Walker 8.9%, squirtle 8.1%, Medic 11.5%, zergling 12.1%, Hunter 13.9%, Random 35% (+1
   share of event-free ticks below 50). Suspected, not verified: these cells take an action every tick that produces
   no event (for example a blocked move or a bite at an empty square), and only a cell that does nothing rests.
8. **Implied rest income per colony (median gain per tick):** Sprint 177 (t0-500), 47 (t500-1000), 15 (t1000-end);
   AtomPush 81 / 47 / 47; AtomCrasher 100 / 36 / 31; Aegis 247 / 198 / 163; Brawler v2 46 / 76 / 90. For comparison,
   whole-match eat transfers per tick are Sprint 75, AtomPush 11, AtomCrasher 38, and feeds AtomPush 618,
   AtomCrasher 283. Sprint's rest income collapses after t500 because 98% of its cell-ticks are event-free but its
   cells are full (only 0.7% of its event-free cell-ticks end +1 after t1000); the Atom colonies keep about 3-4% of
   their cell-ticks gaining, which is about 47 energy per tick for AtomPush all game.
9. **Split parents are not event-tagged:** the replay logs only the child, so a splitting parent shows up as an
   "event-free" cell with a negative delta (-25, -3, -2 ...). This is the "other delta" column (0.03-7.7%); it does
   not change the findings.

## Tables (abridged; all cells in `data/pull2/mining/tables.md`)

Sprint vs AtomPush / AtomCrasher, races with both adjacent:

| rival, window | races | Sprint won % | rival won % | Sprint median child E | rival median child E |
|---|---|---|---|---|---|
| AtomPush, t0-500 | 2373 | 2.4 | 96.6 | 18.5 | 8 |
| AtomPush, t500-1000 | 4428 | 0.9 | 99.1 | 25 | 6 |
| AtomPush, t1000-end | 20538 | 0.3 | 99.7 | 25 | 6 |
| AtomCrasher, t0-500 | 247 | 17.0 | 80.2 | 15 | 13.5 |
| AtomCrasher, t500-1000 | 513 | 5.5 | 90.1 | 25 | 7 |
| AtomCrasher, t1000-end | 6155 | 2.9 | 97.1 | 25 | 6 |

All refills, by the colony that took the square (ticks to refill, child energy for births):

| cell | refills | dt 1 % | dt 2 % | dt 3-5 % | dt > 5 % | median child E | by move % |
|---|---|---|---|---|---|---|---|
| AtomPush | 130689 | 99.1 | 0.5 | 0.2 | 0.2 | 6 | 0 |
| AtomCrasher | 78364 | 97.8 | 1.3 | 0.6 | 0.3 | 6 | 0 |
| Sprint | 62721 | 82.4 | 6.3 | 8.1 | 3.3 | 12 | 0 |
| Brawler | 28166 | 73.4 | 16.9 | 6.6 | 3.2 | 3 | 0 |
| Brawler v2 | 26012 | 80.7 | 16.2 | 3.1 | 0.0 | 7 | 0 |
| Bouncer | 21668 | 75.6 | 13.9 | 9.5 | 1.0 | 3 | 0 |
| Aegis | 18405 | 82.9 | 12.0 | 2.9 | 2.2 | 8 | 0 |
| rooby | 8515 | 96.0 | 3.3 | 0.7 | 0.0 | 21 | 0 |

Resting income (event-free cell-ticks; +1 share overall and below the cap; median colony gain per tick):

| cell | window | event-free % of cell-ticks | +1 % | +1 % (E < 50) | gain / tick |
|---|---|---|---|---|---|
| Sprint | t0-500 / 500-1000 / 1000-end | 96.8 / 97.9 / 98.0 | 15.0 / 2.5 / 0.7 | 96.7 / 95.7 / 94.9 | 177 / 47 / 15 |
| AtomPush | same | 61.6 / 73.5 / 72.5 | 12.1 / 3.9 / 3.7 | 95.2 / 98.1 / 97.5 | 81 / 47 / 47 |
| AtomCrasher | same | 73.8 / 85.5 / 85.9 | 12.2 / 2.5 / 2.3 | 95.7 / 98.5 / 98.1 | 100 / 36 / 31 |
| Aegis | same | 21.1 / 22.4 / 24.0 | 94.1 / 93.6 / 93.6 | 96.5 / 97.0 / 97.7 | 247 / 198 / 163 |
| Brawler v2 | same | 5.8 / 4.5 / 3.9 | 90.5 / 94.8 / 94.7 | 92.1 / 96.8 / 97.6 | 46 / 76 / 90 |
| rooby | same | 93.7 / 92.7 / 91.7 | 14.8 / 0.8 / 1.1 | 95.4 / 84.8 / 90.6 | 101 / 5 / 1 |
| Noob | t0-500 | 90.6 | 6.9 | 6.9 | 9 |
| zergling | t0-500 | 47.1 | 12.0 | 12.1 | 24 |

## Limits

- 35 replays, chosen for pull 2's purposes (17 with Sprint), not a random sample; 98797 has no raw file.
- The replay does not log actions, so "event-free" cannot tell a resting cell from one whose action failed silently;
  finding 7's explanation is a guess. The window income uses all ticks in the window, so matches that end early
  (last colony standing) contribute shorter windows.
- Contenders are fixed at the moment of death; a cell that arrives next to the square by a birth or move one tick
  later is not counted as a contender, but its win still counts as the refill.
- "Move" refills use the mover's start-of-tick energy, not counting gains earlier in the same tick.
