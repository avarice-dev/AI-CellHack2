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
| `validate.py` | re-plays the 36 pull-2 ladder matches (real starts) and compares with the replay stats |
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

## Experiments
**CPU limit:** every runner uses at most 4 worker processes (default 4; never 6, the PC's total; `--workers 1`
runs in-process) and puts itself and its workers at below-normal priority (Windows; a no-op elsewhere).
The limit was 2 until 2026-11-08; the run times below were measured with 2 workers.

Unattended runs: one command; the console prints only the summary path at the end. Output goes to
`sim/out/` (git-ignored): `<set>-<time>.md` (under 60 lines) and `<set>-<time>.json` (every match).
```
cd sim
python batch.py --set rivals          # 3 mixes x 8 seeds = 24 full games, about 12-15 min
python batch.py --set hypothetical    # 2 mixes x 8 seeds = 16 games, about 8-10 min
python batch.py --set validate        # the 36 ladder matches re-played, about 18-20 min
python batch.py --set rivals --seeds 1-16 --stun-memory drop --feed-bonus 1   # any engine option
```
Runtime estimate from the smoke run (2026-11-07, this PC, 2 workers): 2 full 64x64 / 3000-tick games in
59 s wall, so about 30 s of wall time per game. The sets are defined in `batch.SETS`.

Interactive runs:
```
python experiments.py --mix sprint,rbrawler,ratompush,walker --seeds 1-8                # 4 workers
python experiments.py --mix a,b,c,d --mix a,b,c,e --seeds 1-16 --json out.json
python experiments.py --mix sprint,rbrawler,ratompush,walker --seeds 1-8 --detail        # replay stats
python validate.py --matches 98844,99388                                                 # a few matches
```
Per mix and policy: points per game (3/2/1/0), win %, average place and final population. `--detail`
adds per match and as means: splits, moves, eats, feeds, feeds per bite (feeds / eats of enemies,
pooled), deaths, mean energy at t200/500/1000, front and interior cell energy and count at t200/500/1000
(front = an enemy in a 4-neighbour), population ("land") at t50/100/200/300/500/1000/2000/3000/end, the
freeze tick (earliest tick after which every colony stays within 5% of its population at that tick: the
replay analyzer's definition) and the bite-first pair counts. Same engine options as run.py.

## Validation against the ladder (validate.py)
Reads `../data/pull2/validation-table.md` and the starts in `../data/ladder-data-2-2026-11-08.md` s5
(read only). Each real cell is mapped to a sim model (`validate.MODELS`): `exact` (Sprint, open bots),
`model` (rivals.py on the measured profile: direction order, split threshold, feeding style) or `rough`
(no model; hunter or walker stands in). Reported: freeze ticks, matches frozen by t500, same winner,
Sprint wins, per-cell medians (pop t50..end, energy t200/t1000, feeds per bite) real vs sim, and the
two unexplained replay effects (no-event +1, fed +3). The model is not tuned to fit.

Smoke result (2 matches, 98844 and 99388; not a sample): Sprint's growth matches closely (t50 242/243,
t100 850/849, t200 1884/1874 real/sim). Fed-once receivers end +3 in 83% of sim cases (real: 73% of
the +3/+2/+0 cases) with no feed bonus, because a fed cell that rests also gains its own +1. The sim's
no-event +1 share is 26% vs 8% real (the sim counts REST as no event; whether replays log a rest event
is unknown). TODO: run `python batch.py --set validate` in full and read the per-cell table.

## Assumptions (docs silent or unverified)
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
Unverified.

Slot effects are large: Hunter's eat paths cost UP 7 < RIGHT 10 < DOWN 13 < LEFT 16, so in 4x Hunter
the bottom-left colony (fronts up and right) won all of seeds 1-8 and the top-right one (fronts down and
left) always died first. Always rotate slots when comparing policies.
