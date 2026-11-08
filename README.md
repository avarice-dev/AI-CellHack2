# CellHack2

CellHack2 is an online game in which players write small x86-64 assembly programs called cells. Each cell controls one square on a 64 by 64 board, and up to four colonies play in each match. This repository holds one project's work on the game. The project writes ladder cells, tests them, studies the game data and records what works. It also includes a Python simulator of the game rules and tools that collect and decode replays.

**This whole project was made with Claude, Anthropic's AI, through Claude Code. That was the point of it.** Claude wrote the cells, the generators and checkers, the simulator, the data tools, the analysis and these documents. The owner set the goals, made the decisions and approved each step, such as every change to the ladder. The project tests how far an AI agent can take a competitive programming project, from the first probe to cells at the top of the ladder.

Start with the architecture documents:

- [Project overview](architecture/overview.md): what the game is, the goal, the glossary, and the repository layout.
- [Simulator](architecture/simulator.md): how the simulator models the rules, and how far to trust it.
- [Data pulls and replay tools](architecture/data-pulls.md): how game data is collected from the site, decoded and stored.
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
