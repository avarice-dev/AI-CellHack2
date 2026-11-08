# CellHack2

CellHack2 is an online game in which players write small x86-64 assembly programs called cells. Each cell controls one square on a 64 by 64 board, and up to four colonies play in each match. This repository holds one project's work on the game. The project writes ladder cells, tests them, studies the game data and records what works. It also includes a Python simulator of the game rules and tools that collect and decode replays.

**This whole project was made with Claude, Anthropic's AI, through Claude Code. That was the point of it.** Claude wrote the cells, the generators and checkers, the simulator, the data tools, the analysis and these documents. The owner set the goals, made the decisions and approved each step, such as every change to the ladder. The project tests how far an AI agent can take a competitive programming project, from the first probe to cells at the top of the ladder.

Start with the architecture documents:

- [Project overview](architecture/overview.md): what the game is, the goal, the glossary, and the repository layout.
- [Simulator](architecture/simulator.md): how the simulator models the rules, and how far to trust it.
- [Data pulls and replay tools](architecture/data-pulls.md): how game data is collected from the site, decoded and stored.
- [Cells and experiments](architecture/cells-and-experiments.md): how cells are generated and checked, what the calibration probes learned, and the history of each cell.

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

3. Check the cells. Run this in a Linux shell, or in WSL on Windows. NASM, the assembler, must be installed. The Unicorn emulator is optional. At present the run ends with `3 PROBLEM(S)`. The three problems are the VEX cells Woe, Conceit and Endemic. The site runs their VEX compares incorrectly, so the checker flags them on purpose, and they are not submitted. Any other problem is a real failure.

   ```
   python3 cells/check_cells.py
   ```
