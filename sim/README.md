# CellHack2 simulator, stage 1 (rules only)

Pure Python 3.12, stdlib only. Cell programs are Python functions that also report how many
instructions their asm version would run; the engine uses that count for turn order exactly as the real
game does. Stage 2 (later) will run real asm.

Spec: `../docs/Rules _ CellHack2.pdf` (ruleset v9), `../docs/Reference _ CellHack2.pdf`,
`../docs/cellhack.inc` (ABI 4), `../docs/bots/*.asm`.

## Files
| File | What |
|---|---|
| `engine.py` | the rules engine (`Engine`, `View`, constants from cellhack.inc) |
| `bots.py` | the five open bots, ported line by line from `docs/bots/*.asm`, with exact per-path instruction counts |
| `cells_ref.py` | Python references of our own asm cells (`sprint` = `../cells/sprint.asm`, exact path counts) |
| `run.py` | CLI: one match or a seed series, summary tables, optional CSV and ASCII snapshots |
| `rivals.py` | rival reference policies modelled on ladder replays (see below) |
| `policies.py` | registry: policy spec string -> function |
| `experiments.py` | parallel runner for policy mixes over many seeds, replay-style statistics |
| `batch.py` | one command: a named experiment set, unattended, summary .md + full .json in `out/` |
| `validate.py` | re-plays the validation matches of every data pull (real starts) and compares with the replay stats |
| `tests/` | unittest suite (`python -m unittest` from this folder) |

## Running
```
cd sim
python -m unittest                                   # all tests
python run.py                                        # hunter,medic,random,walker; seed 1; 64x64; 3000 ticks
python run.py --bots hunter,idle,medic,walker --seeds 1-20      # series; slots rotate per game
python run.py --bots hunter,walker --size 32 --ticks 500 --csv m.csv --snap m.txt --snap-every 100
python run.py --bots mymodule:mypolicy,hunter        # your own policy (module importable from sim/)
python run.py --bots sprint,rbrawler,ratompush,walker --start corner   # old corner model (default: random)
python run.py --bots rpump,ratompush --stun-memory drop --min-dist 20 --metric chebyshev
python run.py --help                                 # all options (starts, inset, split rounding, ...)
```
The CSV has one row per tick (`tick,pop0..pop3,energy0..energy3`, row N = state after N ticks).
Snapshots show colony letters A-D (upper case at energy >= 25, lower case below), `.` for empty.

## Writing a policy
```python
from engine import ACT_REST, ACT_EAT, ACT_SPLIT, CELL_ENEMY, CELL_EMPTY, VIEW_DIR

def my_cell(view, mem):
    c = view.cells
    for d in range(4):                      # DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT
        if c[VIEW_DIR[d]] == CELL_ENEMY:
            return ACT_EAT + d, 5 + 2 * d   # (action byte, estimated asm instruction count)
    if view.energy >= 6 and c[VIEW_DIR[0]] == CELL_EMPTY:
        return ACT_SPLIT + 0, 14
    return ACT_REST, 15
```
- Signature: `policy(view, mem) -> (action_byte, insn_count)`.
- `view` fields (names follow cellhack.inc): `tick` (0-based), `energy`, `rand` (fresh byte from the
  match RNG), `age` (ticks since birth, saturates at 255), `x`, `y`, `w`, `h`, `pop_self`,
  `pop_enemy` (living cells of all other colonies), `colony` (slot 0-3), `cells` (25 types:
  EMPTY 0, FRIEND 1, ENEMY 2, WALL 3; row-major, self at 12; `VIEW_UP 7, VIEW_RIGHT 13, VIEW_DOWN 17,
  VIEW_LEFT 11`; index of offset (dx, dy) = (dy+2)*5 + (dx+2)), `energies` (25 values, 0 for
  empty/wall). Everything is the start-of-tick snapshot. `view.to_bytes()` gives the 128-byte struct.
- `mem` is the cell's 64-byte `bytearray`; change it in place. It persists between calls and a split
  copies it to the child.
- Keep no other state (no globals, closures or attributes): the asm cell has only `mem`.
- Actions: `0x00` NOP, `0x01` REST, `0x10+d` MOVE, `0x20+d` SPLIT, `0x30+d` EAT, `0x40+d` FEED,
  d = UP 0 (y-1), RIGHT 1 (x+1), DOWN 2 (y+1), LEFT 3 (x-1). Only the low byte is read.
- `insn_count` is your estimate of the asm path length, counting every executed instruction including
  taken jumps and `ret` (the convention used for the bots). Fewest acts first; ties are a seeded coin
  flip. Over 1000 is a budget fault.
- Optional third value: `(action, insn, insn_no_taken_jumps)`, the same path with taken jumps not
  counted. Ignored by default; `Engine(order_by_alt=True)` / `run.py --order-no-taken-jumps` orders
  turns by it instead (totals, averages and the 1000 budget still use `insn`). A policy that returns
  only two values is ordered by `insn` either way. (Excluding `ret` needs no switch: every path has
  exactly one, so it shifts all counts equally and changes no order.)
- Faults (cell does nothing that tick, counted per colony): exception, `None` or malformed return
  (`crash`), unknown action byte (`bad_action`), `insn_count > 1000` (`budget`).

Engine API for experiments: `Engine(policies, width, height, seed, max_ticks, start_inset,
split_child_rounding, cap_mid_tick, self_type, place_start, order_by_alt, start_mode, start_min_dist,
start_metric, start_positions, start_sampler, stun_keeps_memory, record_events, feed_bonus,
idle_gain_prob, record_deltas)`,
`add_cell(x, y, colony, energy, mem, age)`, `step()`, `run()`, `ranking()`, `cells()`, `cell_at(x, y)`.
Per-colony counters of successful actions are always kept: `births` (splits), `deaths`, `stuns`, `moves`,
`feeds`, `eats_enemy`, `eats_friend` (also in `ranking()`). `record_events=True` adds `bite_first[a][b]`:
same-tick pairs of successful eats where colony a's eat came before colony b's in turn order (the
statistic taken from replays).

## Policy registry and rivals
`policies.get(spec)` resolves `name`, `name[k=v,...]` (factory parameters) or `module:function`; run.py
and experiments.py use it, and specs are strings so they reach worker processes. A new family plugs in
by giving its module a `FACTORIES` (name -> factory) and/or `POLICIES` dict and adding the module to
`policies.POLICY_MODULES`.

`rivals.py` (path counts in each docstring; asm sketched in comments):
| Name | Front | Body |
|---|---|---|
| `rbrawler` | static U,L,R,D: 4/6/8/10 (measured, Brawler) | split at 5, poorest-friend feeding (e >= 6, margin 2, target <= 48) |
| `rpump` | as rbrawler | pump: interior (e >= pump_min 16) feeds its richest friend <= 48; cells seeing an enemy hold |
| `ratompush` | static R,L,U,D (measured, AtomPush) | split at 5, feed-assist (e >= 10 -> poor friend with an empty neighbour), capped donors (>= 48) |
| `rblind3` | hypothetical: bites at 3 in every direction, no memory | as rbrawler |
| `rlock5`, `rfatgrab` | hypothetical: checked lock 5 + pre-arm, F6 10 | as rbrawler / ratompush |
| `rblindlock3` | hypothetical (the earlier rblind3): blind lock, first bite 9 then 3, never exits | as rbrawler, no pre-arm |

No measured rival uses a lock: every one checks directions in a fixed order (4 / 6 / >= 8). The lock and
flat-3 variants are labelled hypotheticals, for comparison only.
Options: `order=ULRD`, `front=static|flat3|lock`, thresholds (see the factories), e.g. `rpump[pump_min=12]`.
Speed options (2026-11-08, all off by default): `pad=N` adds N instructions to every non-bite path, and with
`pad_bites_from=k` also to bites in check positions >= k (slow cells: the match-page average insns of rooby,
Noob++ and Aegis is 33-90 while the models ran ~20); `split_after=k` (ratompush and rpump, static front) does
the split check after the first k direction checks, so a hole is refilled in 2k + 13.

## Experiments
**CPU limit:** every runner uses at most 4 worker processes (default 4; never 6, the PC's total; `--workers 1`
runs in-process) and puts itself and its workers at below-normal priority (Windows; a no-op elsewhere).
The limit was 2 until 2026-11-08; the run times below were measured with 2 workers.

Unattended runs: one command; the console prints only the summary path at the end. Output goes to
`sim/out/` (git-ignored): `<set>-<time>.md` (under 60 lines) and `<set>-<time>.json` (every match).
```
cd sim                                # from the repo root
python batch.py --set rivals          # 3 mixes x 8 seeds = 24 full games, about 12-15 min
python batch.py --set hypothetical    # 2 mixes x 8 seeds = 16 games, about 8-10 min
python batch.py --set validate        # every validation match re-played (see the time estimate below)
python batch.py --set rivals --seeds 1-16 --stun-memory drop --feed-bonus 1   # any engine option
```
Runtime estimate from the smoke run (2026-11-07, this PC, 2 workers): 2 full 64x64 / 3000-tick games in
59 s wall, so about 30 s of wall time per game. The sets are defined in `batch.SETS`.
Re-playing real matches (`validate.py`, `batch.py --set validate`, `treadmill.py`) takes about 20 to 80 s of CPU
per match and sim seed (a single match, 1 worker: 19 s, 2026-11-08). So N matches with S seeds take at most
about N x S x 80 s / workers. Count the matches with `--set fit` / `--set test` / `--pull` before a long run.

Interactive runs:
```
python experiments.py --mix sprint,rbrawler,ratompush,walker --seeds 1-8                # 4 workers
python experiments.py --mix a,b,c,d --mix a,b,c,e --seeds 1-16 --json out.json
python experiments.py --mix sprint,rbrawler,ratompush,walker --seeds 1-8 --detail        # replay stats
python validate.py --matches 98844,99388                                                 # a few matches
python validate.py --pull <pull> --set test                                              # one pull's TEST set
python validate.py --models '{"<cell>": "<sim spec>"}'                                   # a model for a cell
python treadmill.py --set fit --workers 2                       # late-game metrics + validate checks
python treadmill.py --set fit --models '{"rooby": "ratompush[...,pad=56]"}'   # try other cell models (JSON or a file)
```
Per mix and policy: points per game (3/2/1/0), win %, average place and final population. `--detail`
adds per match and as means: splits, moves, eats, feeds, feeds per bite (feeds / eats of enemies,
pooled), deaths, mean energy at t200/500/1000, front and interior cell energy and count at t200/500/1000
(front = an enemy in a 4-neighbour), population ("land") at t50/100/200/300/500/1000/2000/3000/end, the
freeze tick (earliest tick after which every colony stays within 5% of its population at that tick: the
replay analyzer's definition) and the bite-first pair counts. Same engine options as run.py.

## Validation against the ladder (validate.py)
Reads `../data/<pull>/validation-table.md` and `../data/<pull>/starts.json` of every data pull (read only).
A data pull is any folder of `../data/` that has a `validation-table.md`; `validate.pulls()` finds them, and
`--pull <pull>` (repeatable) re-plays only those. `tools/replay/valtab.py --pull <pull>` builds both files from a
pull's replays (architecture/data-pulls.md, "Doing your own pull"). Set `CH_DATA` to use another data folder.
Each real cell is mapped to a sim model (`validate.MODELS`): `exact` (Sprint, open bots), `model` (rivals.py on
the measured profile: direction order, split threshold, feeding style) or `rough` (hunter or walker stands in).
A cell that is not in `MODELS` is played by hunter as `rough`, with a warning; `--models` adds models.
The rule statistics and fingerprints printed as "real" are our pull 2 measurements, whatever pulls are re-played. Reported: freeze ticks, matches frozen by t500, same winner,
Sprint wins, per-cell medians (pop t50..end, energy t200/t1000, feeds per bite) real vs sim, and the
two replay effects (no-event +1, fed +3). Both are ordinary rest gains that replays do not log: +1 is a rest, and fed +3 is feed 2 + the target's own rest 1 (Rules p.1-2; docs re-review 2026-11-08). The model is not tuned to fit.

Smoke result (2 matches, 98844 and 99388; not a sample): Sprint's growth matches closely (t50 242/243,
t100 850/849, t200 1884/1874 real/sim). Fed-once receivers end +3 in 83% of sim cases (real: 73% of
the +3/+2/+0 cases) with no feed bonus, because a fed cell that rests also gains its own +1. The sim's
no-event +1 share is 26% vs 8% real (the sim counts REST as no event; whether replays log a rest event
is unknown).

**Validation pool now** (2026-11-08, pull 5): 135 matches, FIT 90 / TEST 45, fixed per match in
data/splits/split.json (`validate.split_sets` reads it). Pulls 2-4 keep their sets (63: FIT 42 / TEST 21, the
stratified rule over their own ids); pull 5 (72: FIT 48 / TEST 24) was split alone by the same rule (seed
SPLIT_SEED = 20261108). New matches: `python validate.py --extend-split` (old entries never change).
`--split <file>` uses another FIT/TEST file (for example one for your own pull); give it to every run.

**Hold-out split** (history; fixed 2026-11-07, before any tuning; `validate.split_sets`): the 36 match ids sorted,
every third one (positions 2, 5, 8, ...) is TEST (12: 98797, 98854, 98911, 98989, 99074, 99109, 99134,
99208, 99239, 99304, 99371, 99420), the other 24 are FIT. Tuning looks at FIT runs only
(`python validate.py --set fit --workers 3`); TEST is run only to judge. Caveat: the rival fingerprints of
ladder data s4 are pooled over all replays, TEST ones included. The report ends with the acceptance
checks (`validate.thresholds`) per set and a fingerprint table (front / interior energy t500/t1000 and
split mode, real s4 vs sim). "E200 / E1000" in the checks is the colony mean energy of the table.

### Treadmill metrics (treadmill.py)
Late-game targets from pull 3 (data/scourge-losses-2026-11-08.md), computed the same way for the real replays
(data/<pull>/mining/races/*.csv.gz of every data pull; populations from summaries pop10 or mining pop) and the
sim (`Engine(record_races=True)`, one row per death as in tools/replay/mine.py): per cell, the share of its refilled death squares it refilled itself, its
deaths per tick in t < 500 / 500-1000 / >= 1000, the median pop change t500 -> end, the first tick at pop 128
/ 512, and contested races per opponent (deaths of either with both adjacent, won by whom). It also prints
validate.py's report and checks and the sim's average insns per call (compare with the match pages).
tools/replay/actions.py gives per-cell action shares at the front from a real replay (eat direction, bitten
first, split, none) for comparing with the sim.

### Calibration log
Each line: change, then FIT (and TEST when run) results. sw = same winner (no rough / all), fz = freeze
median sim vs real, f500 = frozen by t500, Sp = Sprint wins.

## Assumptions (docs silent or unverified)

Docs re-review 2026-11-08: the Rules support the defaults of 4 (cap at Tidy, stated), 5 and 6 (implied by
Decide before Act), and 7 (newborns act from the next tick); 6b has no basis in the docs (no feed bonus,
no passive gain). 1 (starts), 2 (rounding) and 3 (self type) are not in the docs.
Parameters let you flip the ones marked (param).
1. **Start squares** (param `start_mode`). Verified 2026-11-08 from replays: ladder starts are random
   squares (e.g. 98753: (10,61) (23,30) (45,21) (13,41); more in `../data/ladder-data-2026-11-08.md` s5).
   `random` (default in run.py and experiments.py) draws each start uniformly over the board, conditioned
   on a minimum pairwise distance (`start_min_dist` 8, `start_metric` manhattan: the smallest closest
   pair in the 36 pull-2 replays is Manhattan 8). Real starts sit near an edge slightly less often than
   uniform ones (19% vs 29% within 4 squares); not modelled. The true distribution is unknown:
   change it via `start_sampler` (name in `engine.START_SAMPLERS` or a callable `(rng, w, h, n)`), or
   use `fixed` with `start_positions`. `corner` (Engine default, kept for the old tests): one cell per
   corner, inset `start_inset`; slot 0 top-left, 1 top-right, 2 bottom-left, 3 bottom-right.
2. **Split rounding** (param `split_child_rounding`, default `floor`): child gets floor(e/2), parent
   keeps the rest (7 -> parent 4, child 3; 5 -> parent 3, child 2).
3. **Self at view index 12** (param `self_type`, default CELL_FRIEND); `energies[12]` = own energy.
4. **Mid-tick cap** (param `cap_mid_tick`, default False): energy may exceed 50 between gains and Tidy
   and can be spent (e.g. a capped cell fed to 52 splits 26/26), as the rules text puts the cap in Tidy.
5. **Newborn memory** is copied at the moment of the split, so it includes the parent's writes from the
   splitting call.
6. **Memory writes persist when the cell is stunned** (param `stun_keeps_memory`, default True; run.py
   `--stun-memory keep|drop`): the call already ran. With False, a cell bitten before its turn gets its
   pre-call memory back (as if its code never ran). Writes also persist when the call faults.
6b. **Unexplained replay effects, off by default** (params `feed_bonus`, `idle_gain_prob`; run.py
   `--feed-bonus N`, `--idle-gain P`): a fed cell gains 2 + `feed_bonus`; a cell with no event and no
   REST gains +1 with probability `idle_gain_prob` (own RNG, so the match RNG stream is unchanged).
   `record_deltas=True` keeps the energy-change histograms used to compare with the replays.
7. **Newborns are on the board at once**: they block moves/splits and can be eaten or fed in their birth
   tick; they take no turn until the next tick (age 0 then).
8. **VIEW_RAND order**: one byte per living cell per tick, drawn in cell birth order, including cells that
   then fault. The real engine's draw order and tie-shuffle algorithm are unknown, so seeds do not
   reproduce real matches.
9. **Tie shuffle**: the act list is shuffled with the match RNG, then stably sorted by insn_count.
10. **Instruction totals with faults**: a budget fault adds 1001 to the colony's total/max; a bad_action
    adds the reported count; a crash adds nothing and is not counted as a call.
11. **NOP** cells are left out of the turn order (no observable difference: NOP does nothing and a stun
    takes nothing from it).
12. **insn_count must be a non-negative int**; anything else is a `crash` fault (simulator-only check).
13. **Colony death tick** = the tick during which its last cell died (a colony with no cells at the start
    counts as dead at tick 0); "how long they lasted" compares these.
14. **"One colony left"** ends a match only if it started with more than one colony.
15. **Points** with fewer than 4 colonies: 3, 2, 1 top-down.
16. **Ranking energy** = total energy after the final Tidy (capped).
17. **Memory size** is forced back to 64 bytes if a policy resizes the bytearray.

## Bots
Ported from `docs/bots/*.asm` (real thresholds: Hunter/Medic/Walker/Random split or act at e >= 6, Medic
feeds up at e >= 15). Instruction counts per path (every executed instruction incl. taken jumps and
`ret`): Hunter eat 7/10/13/16 (UP/RIGHT/DOWN/LEFT), rest 17, split 20; Medic rest 6, split 9 (e < 15) or
13 (e >= 15, no friend above), feed 9; Random rest 4, else 14; Walker split 7, rest 7, move 9; Idle 2.
Hunter, Medic and Walker split in a random direction without checking the square, so a split at an
occupied square wastes the tick.

Without taken jumps (third value): Hunter eat 6/9/12/15, rest 16, split 20; Medic rest 4, split 8 or 12,
feed 9; Random rest 3, else 14; Walker split 7, rest 5, move 8; Idle 2.

Note: Hunter's split path is 20 by this convention while the Rules say "the bots use fewer than 20".
That path has no taken jumps, so only not counting `ret` would make it 19; or the sentence is loose.
Settled 2026-11-08: the sentence is loose. The Reference says "The engine counts every instruction"
(p.3), and the site's match pages show Hunter at 19 (20).

Slot effects are large: Hunter's eat paths cost UP 7 < RIGHT 10 < DOWN 13 < LEFT 16, so in 4x Hunter
the bottom-left colony (fronts up and right) won all of seeds 1-8 and the top-right one (fronts down and
left) always died first. Always rotate slots when comparing policies.
- 2026-11-07 baseline (sim 909c432 models): FIT sw 4/7, 17/24; fz 2632 vs 2106; f500 0 vs 0; Sp 9/12 vs 12/12;
  31/63 checks pass. Pump colonies E200 28-32 vs 10-13 real; AtomCrasher f/eat 27 vs 7; fed +3 85% vs 73%.
- it1, pumps (Brawler, Brawler v2, Bouncer, Aegis, Noob+, Noob++): `hold=none,target=poorest,pump_min=10,
  pump_target_max=50` (sweep on 6 FIT matches to t1000: richest-target pumps kept interior 18-21; poorest 7/10/13
  gave interior 11/14/17). Fingerprints now fit (interior t500 13-15 vs 9-19 real, front 16-30). FIT sw 3/7, 16/24;
  fz 2426 vs 2106; Sp 8/12; 37/63 checks. TEST sw 1/5, 7/12; fz 2684 vs 1810; Sp 2/5 vs 3/5; 46/62. Winners worse
  than baseline: thin pumps still hold land (Brawler t1000 1733 vs 16 real) and both Atoms collapse late
  (AtomPush end 1 vs 1370), so Sprint's late growth is short (t1000 1840 vs 2426).
- it2, AtomPush and AtomCrasher `split_after=2` (refill a hole in 17 < Sprint's 19-23; mining: Atoms take 99% of
  contested holes from Sprint). FIT sw 3/7, 16/24; fz 2807 vs 2106; Sp 7/12; 42/63 checks (it1 37). AtomPush front
  t500 23.5 vs 22 real (it1 29); AtomCrasher now holds too much (end 2752 vs 1664). Sprint late growth still short.
- it3, pumps `target=richest,pump_min=8` (uphill to the front instead of poorest). FIT sw 4/7, 17/24; fz 2276 vs
  2106 (pass); Sp 8/12; 44/63 checks. Interior 18 vs 9-13 real (pump colony E200 17-18 vs 10, just outside +-6),
  pump f/eat 14-27 vs 18-59; Sprint t500 1699 vs 2504.
- it4, pumps `pump_min=5` (feed whenever boxed in). FIT sw 3/7, 16/24; fz 2212 vs 2106; Sp 7/12; 49/63 checks.
  Interior t500 15-17 vs 9-19. Still: pumps hold land after t500 (Noob+ t1000 1606 vs 2, Brawler 915 vs 11).
- it5 (reverted), Atoms `donor_min=50` (+ AtomCrasher `assist_min=20`): f/eat 32/23 vs 17/7, fed +3 share fell
  to 10% (receivers busy), 47/63 checks. No improvement.
- it6 (reverted), pumps `pump_target_max=30` (front t500 too fat for Aegis/Noob+): interior filled to 49, f/eat 2-6,
  29/63 checks. Same winners as it4 (16/24, Sp 7/12): winners barely react to the pump economy.
- Final (it4 models), full 36 (`out/final-it4.txt`, not committed): all sw 26/36, no-rough 6/12; fz 2272 vs 2061;
  f500 1 vs 2; Sp 10/17 vs 15/17 (baseline 26/36, 6/12, 2617, 13/17). TEST 47/62 checks: pass winner(all) 10/12,
  Sprint wins 3/5, Sprint pops, fed +3 77%; fail winner(no rough) 3/5, freeze 2302 vs 1810, f/eat of Aegis,
  AtomCrasher, Bouncer, Brawler, Brawler v2, Noob++, some t200 pops. FIT 49/63; fails Sprint wins 7/12 and
  Sprint t500/t1000 pops. Stopped (it5, it6 no gain). Blocker: thin pump colonies keep their land after t500
  (sim Brawler/Noob+ t1000 900-1600 vs 2-16 real) whatever their economy, so the fight/refill model, not the
  feeding, is what is off; do not trust the sim for Sprint-vs-pump outcomes or late-game land.
- 2026-11-08 treadmill pass (`treadmill.py`, outputs `out/treadmill-{fit,test}-*.txt`, not committed). Measured first: the
  engine matches the rules (no cell acts after being bitten in 562k real turns of 98964; refills only next tick), so
  the gap is in the rival models. Evidence: (a) match-page avg insns: Noob++ 73-90, rooby 58-79, Aegis 32-35 vs the
  models' ~20-24 (Sprint 19 (21/23), Hunter, Medic, Walker match exactly, so the column is reliable); (b) contested
  refills (FIT, real / sim): Sprint vs Noob++ 77 / 50%, Aegis vs rooby 81-97 / 38-46%; (c) real birth order
  (`tools/pull2/birth_order.py`, t >= 300): Brawler, Brawler v2, Bouncer and the Atoms split before Sprint in 100% of
  shared ticks, Noob+ / Aegis / rooby / Noob++ after it in 94-100%.
  pad1 (non-bite pad: Noob++ 66, rooby 56, Aegis 12): FIT 49/63. pad3 (also slow-direction bites:
  `pad_bites_from` 1 / 2 / 1): FIT 46/63, TEST 49/62 (base TEST 47/62); land t500->end now right for Noob++,
  Aegis, rooby (-1.00 like real), contested shares vs Sprint match (Noob++ 74-79 vs 77-78%). pad2 / pad4 (pad3 +
  pump `split_after` 2 / 3 from (c)): FIT 48 / 47; overshoot (Sprint vs Brawler contested 31-35% vs real 43-57%).
  Not adopted (FIT does not improve; defaults unchanged). Still off: Noob+ and Brawler v2 keep land (t500->end
  +0.06 / +0.85 vs -1.00 / -0.49 FIT), front deaths per tick of thin pumps about half of real early (Brawler 3.5 vs
  6.7, Noob+ 0.8 vs 3.7), Atom f/eat 2-6x. Candidate (pad3, `--models`): Noob++ = Noob+ spec + `pad=66,pad_bites_from=1`; rooby = its spec +
  `pad=56,pad_bites_from=2`; Aegis = its spec + `pad=12,pad_bites_from=1`.
