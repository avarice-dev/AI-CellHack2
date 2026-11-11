# CellHack2

CellHack2 is an online game in which players write small x86-64 assembly programs called cells. Each cell controls one square on a 64 by 64 board, and up to four colonies play in each match. This repository holds one project's work on the game. The project writes ladder cells, tests them, studies the game data and records what works. It also includes a Python simulator of the game rules and tools that collect and decode replays.

**This whole project was made with Claude, Anthropic's AI, through Claude Code. That was the point of it.** Claude wrote the cells, the generators and checkers, the simulator, the data tools, the analysis and these documents. The owner set the goals, made the decisions and approved each step, such as changes to the ladder. The project tests how far an AI agent can take a competitive programming project, from the first probe to cells at the top of the ladder.

## Cell names

The cells are named after Necroid ship classes from the game Stellaris. The calibration probes are the exception. The table covers each cell that has played on the ladder, and the planned cells.

| Cell | How it plays | Peak place | Peak rating | Latest or final place | Latest or final rating |
|---|---|---|---|---|---|
| Avarice | Hoards energy: eats greedily and never feeds other cells. | 7th* | 1355* | 9th (retired) | 1191 |
| Covetous | Goes after its neighbours, with a fast bite in every direction. | 3rd* | 1526* | 7th (retired) | 1392 |
| Scourge | Kills and occupies: refills the squares freed in fights. | 1st | 1649* | 2nd (retired) | 1507 |
| Contagion | Spreads quickly, with extra rules for the early land grab. | 1st | 1631* | 2nd (retired) | 1616 |
| Complacency | Ignores nearby enemies and keeps splitting. | 1st* | 1608* | 2nd (retired) | 1516 |
| Schism | Splits outward quickly, with inner cells feeding the edge. | 1st | 1675* | Retired 2026-11-11 | 1314 |
| Pestilence | Moves strong cells into freed squares, carrying energy to the front. | 2nd | 1576 | Retired 2026-11-11 | 1250 |
| Bane (v1) | Schism that holds back near enemies: no weak children next to a faster biter, so its border cells survive the grab. | 10th | about 1300 | Retired | 1307 |
| Bane v2 (v2.1, then v2.2) | Spreads out, then keeps biting: children walk away from their parent before they settle, so cells are not boxed in, and a cell that just bit an enemy bites the same square again at once. A bane is something that ruins its prey, and this cell eats the enemy squares beside it. | 1st | 1804 | On the ladder (v2.2) | 1706 |
| Conviction | Acts on what it believed last tick: after one look it bites the same square for several ticks without looking again, which makes its bite the fastest we have. Bane's opening. | 3rd | 1635 | On the ladder | 1635 |
| Penalty | Conviction that makes the enemy pay with its square: when its target is about to die, its next stored action is a split into that square. A test cell. | - | - | On the ladder (tester) | - |

Rows for Avarice to Contagion and Complacency: as of 2026-11-10 06:05 UTC-06. Schism, Pestilence and the Bane rows: read from the site's My cells page on 2026-11-11. Final or latest figures and games played: Schism 1314 after 2814 games (retired by the owner because it was the lowest rated of the three ladder cells); Pestilence 1307 after 1467 games; Bane v1 1307 after 44 games; Bane v2.1 1804 after 203 games (an earlier read the same day was 1775 after 189 games, 175 wins, average place 1.07, 1st). The ladder now holds two cells, Bane and Pestilence. The Bane v1 peak place (10th) and the 1st for v2.1 come from earlier reads. Bane v2.0 (retired at 1645 after 157 games, 1st) and v2.2 (on the ladder since 2026-11-11 15:05 UTC in place of v2.1; no result yet) are described in [Cells and experiments](architecture/cells-and-experiments.md). \* Best recorded value; the site does not publish peaks. Later reads on 2026-11-11: Pestilence was taken off the ladder at 1250 after 1649 games to free a slot for test cells; Bane v2.2 1706 after 184 games (v2.1's last figure was 1804 after 203); Conviction 1635 after 155 games; Penalty had just started.

## Documents

Start with the architecture documents:

- [Project overview](architecture/overview.md): what the game is, the goal, the glossary, and the repository layout.
- [Simulator](architecture/simulator.md): how the simulator models the rules, and how far to trust it. The engine is complete and checked against replays; accurate models of rival cells are the user's own work.
- [Data pulls and replay tools](architecture/data-pulls.md): how game data is collected from the site, decoded and stored. Pulling and decoding are complete. The analysis tools are an open set: add the measures that your own cell needs.
- [Cells and experiments](architecture/cells-and-experiments.md): how cells are generated and checked, what the calibration probes learned, and the history of each cell.
- [Cell assembly](architecture/cell-assembly.md): the x86-64 instructions in the cells, why each one was chosen, and how each decision is written in code.

## Quick start

Run these commands from the root of the repository.

1. Run the simulator's unit tests. Python 3.12 is needed. The simulator uses only the standard library.

   ```
   cd sim
   python -m unittest
   ```

2. Run a simulator batch. The `rivals` set plays 24 games and takes about 12 to 15 minutes. For a quick test, add `--seeds 1` (about 1 minute). The console prints the path of the summary file. The results go to `sim/out/`.

   ```
   cd sim
   python batch.py --set rivals
   ```

3. Check the cells. Run this in a Linux shell, or in WSL on Windows. NASM, the assembler, must be installed. The Unicorn emulator is optional. Without it, the checker skips the instruction-count and reference checks.

   Install NASM with the system package manager. On Ubuntu or WSL: `sudo apt install nasm`. On Windows, `winget install NASM.NASM` installs NASM, but the checker has been run only in Linux and in WSL. Install Unicorn in a virtual environment, from `requirements-checker.txt`:

   ```
   python3 -m venv .venv-checker
   . .venv-checker/bin/activate
   pip install -r requirements-checker.txt
   python3 cells/check_cells.py
   ```

   Versions known to work: NASM 3.01, Unicorn 2.1.4, Python 3.12 (Python 3.14 also works). The VEX cells Woe, Conceit and Endemic always fail the check. The site runs their VEX compares incorrectly, so the checker flags them on purpose, and they are not submitted. The checker reports their problems as expected failures (3 without Unicorn, 33 with Unicorn). It ends with `ALL OTHER CHECKS PASSED` and exit code 0 when only these cells fail. Any problem in another cell is a real failure: the checker prints `PROBLEM(S) in:` with the cell names, and exits with code 1.

4. Use the replay tools. The replays are not in the repository. To decode replays, do your own pull first: see "Doing your own pull" in [data-pulls.md](architecture/data-pulls.md). Each replay tool is in `tools/replay/` and takes the pull as `--pull <pull>`; there is no default pull. The tools that need no replays (for example `python -I tools/replay/tab.py --pull pull3 --cell Scourge`) also run on the stored match lists of our pulls.
