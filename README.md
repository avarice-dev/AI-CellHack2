# CellHack2

CellHack2 is an online game in which players write small x86-64 assembly programs called cells. Each cell controls one square on a 64 by 64 board, and up to four colonies play in each match. This repository holds one project's work on the game. The project wrote ladder cells, tested them, studied the game data and recorded what worked. It also holds a Python simulator of the game rules and tools that collect and decode replays.

**The project is likely done being updated.** No further work is planned.

**This whole project was made with Claude, Anthropic's AI, through Claude Code.** Claude wrote the cells, the generators and checkers, the simulator, the data tools, the analysis and these documents. The owner set the goals, made the decisions and approved each step that touched the ladder. An external reviewer gave directions in the last days. The project tested how far an AI agent can take a competitive programming project, from the first probe to cells near the top of the ladder.

## Outcome

The goal was a cell that takes first place on the ladder and stays there. The project did not reach it.

- The best cell was **Misfortune v3** (cell 353). At the last check, on 2026-11-14 at 16:47, it was rated 1841 after 441 games, with an average place of 1.17, in third place. The leader, Siect-F, was rated 2053.
- Earlier cells of ours held first place for a while: Scourge, Contagion, Complacency, Schism and Bane v2.
- The last two builds did not help. **Depravity** (cell 363) went on the ladder on 2026-11-14 and was retired after 5 games at rating 1193. **Dogma** was built and checked, but its local results did not beat Misfortune v3, so it was never uploaded.
- What the project learned is in [Cells and experiments](architecture/cells-and-experiments.md) and in [the last-round review](reviews/final-round-2026-11-13-14.md).

## Cell names

The cells are named after Necroid ship classes from the game Stellaris. The calibration probes are the exception. The table covers each cell that played on the ladder and the last cell built. Peak figures marked with `*` are the best recorded values, because the site does not publish peaks. The full status table is in [Cells and experiments](architecture/cells-and-experiments.md#final-ladder-status).

| Cell | How it plays | Peak place | Last rating | Final state |
|---|---|---|---|---|
| Avarice | Hoards energy: eats greedily and never feeds other cells. | 7th* | 1191 | Retired. |
| Covetous | Goes after its neighbours, with a fast bite in every direction. | 3rd* | 1392 | Retired. |
| Scourge | Kills and occupies: refills the squares freed in fights. | 1st | 1507 | Retired. |
| Contagion | Spreads quickly, with extra rules for the early land grab. | 1st | 1616 | Retired. |
| Complacency | Ignores nearby enemies and keeps splitting. | 1st* | 1516 | Retired. |
| Schism | Splits outward quickly, with inner cells feeding the edge. | 1st | 1314 | Retired 2026-11-11. |
| Pestilence | Moves strong cells into freed squares, carrying energy to the front. | 2nd | 1250 | Retired 2026-11-11. |
| Bane (v1) | Schism that holds back near enemies: no weak children next to a faster biter, so its border cells survive the grab. | 10th | 1307 | Retired. |
| Bane v2 (v2.0, v2.1, v2.2) | Spreads out, then keeps biting: children walk away from their parent before they settle, and a cell that just bit an enemy bites the same square again at once. A bane is something that ruins its prey, and this cell eats the enemy squares beside it. | 1st | 1761 (v2.2) | Retired 2026-11-13. |
| Conviction | Acts on what it believed last tick: after one look it bites the same square for several ticks without looking again. | 3rd | 1635 | Off the ladder. |
| Penalty | Conviction that makes the enemy pay with its square: when its target is about to die, its next stored action is a split into that square. A test cell. | none | none | Tester. |
| Misfortune v1 | Bites without looking: after one look at an enemy beside it, it writes down its next bites by its own energy. Each later bite takes 2 instructions, the fewest the game allows. The name fits because whoever bites it is bitten first on the next tick. | 2nd | 1751 | Replaced by v2. |
| Misfortune v2 | v1 plus a checked refill, armed children and no prey hold. It failed: a slower first bite and more friendly bites. | none | 1326 | Retired after 9 games. |
| **Misfortune v3** | v1 plus one change: a cell with 10 or more energy splits even with an enemy near. | 2nd | 1841 | **Live at the end: 3rd.** |
| Depravity | A clean-sheet cell with a faster arm step and no energy cap on the rear. It failed against AtomVirus and VarSi. | none | 1193 | Retired after 5 games. |
| Dogma | A 3-instruction counter bite with a walker opening. It beat every rival model locally and lost to Misfortune v3. | none | none | Never uploaded. |

The Woe, Conceit and Endemic cells are VEX forms that the site runs wrongly. They were never on the ladder.

## Documents

Start with the architecture documents:

- [Project overview](architecture/overview.md): what the game is, the goal and outcome, the glossary, the repository layout, and an index of `reviews/` and `briefs/`.
- [Cells and experiments](architecture/cells-and-experiments.md): how cells are generated and checked, what the calibration probes learned, the lineage of every cell and the final ladder status.
- [Cell assembly](architecture/cell-assembly.md): the x86-64 instructions in the cells, why each one was chosen, and how each decision is written in code.
- [Simulator](architecture/simulator.md): how the simulator models the rules, and how far to trust it.
- [Data pulls and replay tools](architecture/data-pulls.md): how game data was collected from the site, decoded and stored, and which parts are local only.

Other documents:

- [designs.md](designs.md): the design notes, with a final-state summary at the top.
- [reviews/](reviews/final-round-2026-11-13-14.md): design reviews and decision records. Start with the last-round review.
- [briefs/](briefs/misfortune-spec-2026-11-13.md): dated working briefs and hand-over notes.
- [docs/evidence/](docs/evidence/ladder-data-2-2026-11-08.md): six study notes with the measurements that the code comments cite.

## Layout

| Folder | What it holds |
|---|---|
| `architecture/` | The architecture documents above. |
| `cells/` | Cell generators (`gen_*.py`), the assembly they write (`*.asm`), the checker `check_cells.py` and the calibration probes. |
| `sim/` | The simulator, its runners and its tests. See [sim/README.md](sim/README.md). |
| `tools/` | Replay tools (`tools/replay/`), the opening search (`tools/search/`) and the tests of the tools. |
| `docs/` | The game rules (PDF), `cellhack.inc`, the open bots and `docs/evidence/`. |
| `reviews/`, `briefs/` | Reviews and dated briefs. |
| `data/` | **Local only, not in the repository.** See below. |

## What is local only

The `data/` folder is not published. It held the replays, the pulled match lists, the mining output, the validation tables, the FIT and TEST split and the site-check log. Git ignores it. The tools in `tools/replay/` rebuild the match data from the site. See [data-pulls.md](architecture/data-pulls.md).

This affects the tests. The simulator validation (`sim/validate.py` and the FIT and TEST check in `sim/tests/test_reference_data.py`) needs local pulls: `data/<pull>/validation-table.md`, `data/<pull>/starts.json` and `data/splits/split.json`. It cannot run from a clean clone. Everything else below runs from a clean clone, with the tools it names.

Many documents and code comments name files under `data/`. Those names point to the local folder. Copies of the six notes that the code cites are in `docs/evidence/`.

## Quick start

Run these commands from the root of the repository.

1. Run the simulator's unit tests. Python 3.12 is needed. The simulator uses only the standard library. In a clean clone, `tests/test_reference_data.py` reads `data/` and fails (10 of its 11 tests). All other simulator tests pass.

   ```
   cd sim
   python -m unittest
   ```

   The tool tests run from the repository root with `python -m unittest discover -s tools/tests`.

2. Run a simulator batch. The `rivals` set plays 24 games and takes about 12 to 15 minutes. For a quick test, add `--seeds 1` (about 1 minute). The console prints the path of the summary file. The results go to `sim/out/`.

   ```
   cd sim
   python batch.py --set rivals
   ```

3. Build and check a cell. Run this in a Linux shell, or in WSL on Windows. NASM, the assembler, must be installed. The Unicorn emulator is optional. Without it, the checker skips the instruction-count and reference checks.

   Install NASM with the system package manager. On Ubuntu or WSL: `sudo apt install nasm`. The checker was run only in Linux and in WSL. Install Unicorn in a virtual environment, from `requirements-checker.txt`:

   ```
   python3 -m venv .venv-checker
   . .venv-checker/bin/activate
   pip install -r requirements-checker.txt
   python3 cells/gen_misfortune2.py      # writes cells/misfortune2.asm (Misfortune v3)
   python3 cells/check_cells.py --only misfortune2
   ```

   Each cell has a generator `cells/gen_<name>.py` that writes `cells/<name>.asm`. Run the checker without `--only` (all cells) when `docs/cellhack.inc`, `check_cells.py` or a shared reference changes.

   Versions known to work: NASM 3.01, Unicorn 2.1.4 and Python 3.12 (Python 3.14 also works).

   The VEX cells Woe, Conceit and Endemic always fail the check. The site runs their VEX compares wrongly, so the checker flags them on purpose, and the project never submitted them. The checker reports their problems as expected failures. When only these cells fail, it ends with `ALL OTHER CHECKS PASSED` and exit code 0. A problem in any other cell is a real failure. The checker then prints `PROBLEM(S) in:` with the cell names and exits with code 1.

4. Use the replay tools. The replays are not in the repository. To decode replays, do your own pull first: see "Doing your own pull" in [data-pulls.md](architecture/data-pulls.md). Each replay tool is in `tools/replay/` and takes the pull as `--pull <pull>`; there is no default pull.


## Known limitations

- The simulator is weak for fights against rival cells. Local results did not predict ladder results for the last cells.
- The simulator validation needs local data that is not published.
- Dogma and the Depravity hotfix were never uploaded, so only the local engine judged them.
- The final results of Conviction and Penalty were not recorded.
