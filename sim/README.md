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
| `run.py` | CLI: one match or a seed series, summary tables, optional CSV and ASCII snapshots |
| `tests/` | unittest suite (`python -m unittest` from this folder) |

## Running
```
cd sim
python -m unittest                                   # all tests
python run.py                                        # hunter,medic,random,walker; seed 1; 64x64; 3000 ticks
python run.py --bots hunter,idle,medic,walker --seeds 1-20      # series; slots rotate per game
python run.py --bots hunter,walker --size 32 --ticks 500 --csv m.csv --snap m.txt --snap-every 100
python run.py --bots mymodule:mypolicy,hunter        # your own policy (module importable from sim/)
python run.py --help                                 # all options (inset, split rounding, mid-tick cap...)
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
split_child_rounding, cap_mid_tick, self_type, place_start)`, `add_cell(x, y, colony, energy, mem, age)`,
`step()`, `run()`, `ranking()`, `cells()`, `cell_at(x, y)`.

## Assumptions (docs silent or unverified)
Parameters let you flip the ones marked (param).
1. **Start squares** (param `start_inset`, default 0): one cell per true corner. Slot to corner:
   0 top-left, 1 top-right, 2 bottom-left, 3 bottom-right (the docs only say "one per corner").
2. **Split rounding** (param `split_child_rounding`, default `floor`): child gets floor(e/2), parent
   keeps the rest (7 -> parent 4, child 3; 5 -> parent 3, child 2).
3. **Self at view index 12** (param `self_type`, default CELL_FRIEND); `energies[12]` = own energy.
4. **Mid-tick cap** (param `cap_mid_tick`, default False): energy may exceed 50 between gains and Tidy
   and can be spent (e.g. a capped cell fed to 52 splits 26/26), as the rules text puts the cap in Tidy.
5. **Newborn memory** is copied at the moment of the split, so it includes the parent's writes from the
   splitting call.
6. **Memory writes persist when the cell is stunned** (the call already ran), and also when the call
   faults.
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
