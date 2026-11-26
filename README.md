# CellHack2

CellHack2 is an online game in which players write small x86-64 assembly programs called cells. Each cell controls one square on a 64 by 64 board, with up to four colonies per match. This repository holds one project's ladder cells, generators, checker, Python simulator, and replay tools.

**No further work is planned.** Claude (Anthropic's AI, via Claude Code) wrote the cells, generators, checkers, simulator, data tools, analysis, and documentation; the owner set the goals and approved every ladder change, and an external reviewer gave directions in the final days.

## Outcome

The goal was a cell that takes and holds first place on the ladder. The project did not reach it:

- **Best cell:** **Misfortune v3** (cell 353) was rated 1841 after 441 games (average place 1.17, 3rd place) at the last check on 2026-11-14 at 16:47; the leader, Siect-F, was rated 2053.
- **Earlier leaders:** Scourge, Contagion, Complacency, Schism, and Bane v2 held 1st place at earlier points.
- **Final builds:** **Depravity** (cell 363) was retired after 5 ladder games at rating 1193; **Dogma** was built and checked locally, did not beat Misfortune v3 in the simulator, and was never uploaded.

For the full cell lineage, instruction counts, and final ladder status, see [Cells and experiments](architecture/cells-and-experiments.md). For the final-round narrative, see [the last-round review](docs/archive/reviews/final-round-2026-11-13-14.md). For known limitations across the simulator, data, and ladder records, see [Project overview](architecture/overview.md#known-limitations).

## Documents

Start with the canonical architecture documents:

- [Project overview](architecture/overview.md): game rules summary, goal and outcome, glossary, workflow diagram, reading order, repository layout, and known limitations.
- [Cells and experiments](architecture/cells-and-experiments.md): cell generators, checker, calibration probes, simulator experiments, cell lineage, and final ladder status.
- [Cell assembly](architecture/cell-assembly.md): x86-64 instructions used in the cells and why each decision is written that way.
- [Simulator](architecture/simulator.md): how the Python simulator models the rules and how far to trust it (see also [sim/README.md](sim/README.md)).
- [Data pulls and replay tools](architecture/data-pulls.md): how game data was collected and decoded, and what stays local.

Historical records and evidence:

- [Historical documentation archive](docs/archive/README.md): archived `designs.md`, dated `reviews/`, and `briefs/` (2026-11-07 to 2026-11-14), with a legacy-path mapping.
- [docs/evidence/](docs/evidence/ladder-data-2-2026-11-08.md): six study notes with measurements cited by code comments.

## Layout

| Folder | What it holds |
|---|---|
| `architecture/` | Canonical architecture documents. |
| `cells/` | Cell generators (`gen_*.py`), generated assembly (`*.asm`), `check_cells.py`, `vex_emu.py`, and `calib/` probes. |
| `sim/` | Python simulator, batch runners, and unit tests. See [sim/README.md](sim/README.md). |
| `tools/` | Replay tools (`tools/replay/`), opening search (`tools/search/`), and tool tests (`tools/tests/`). |
| `docs/` | Official game rules (PDF), `cellhack.inc`, open bots (`docs/bots/`), `docs/evidence/`, and `docs/archive/`. |
| `data/` | **Local only, not in the repository.** See below. |

## What is local only

The `data/` directory is git-ignored and not published. It held replays, pulled match lists, mining output, validation tables, the FIT/TEST split, and the site-check log (see [data-pulls.md](architecture/data-pulls.md)).

In a clean clone, `sim/validate.py` and the FIT/TEST checks in `sim/tests/test_reference_data.py` (10 of its 11 tests) fail because they read `data/`. Everything else below runs from a clean clone. Copies of the six study notes cited by code comments live in `docs/evidence/`.

## Quick start

Run these commands from the repository root (Python 3.12+ recommended; the simulator uses only the standard library).

1. **Unit tests:**
   ```bash
   cd sim && python -m unittest
   python -m unittest discover -s tools/tests
   ```
   *(In a clean clone, 10 of 11 tests in `sim/tests/test_reference_data.py` fail without `data/`; all other simulator and tool tests pass.)*

2. **Simulator batch:**
   ```bash
   cd sim && python batch.py --set rivals
   ```
   Plays 24 games (~12–15 minutes; add `--seeds 1` for ~1 minute) and writes results to `sim/out/`.

3. **Build and check a cell** (Linux or WSL with NASM; Unicorn in a venv is optional for emulation checks; known working versions: NASM 3.01, Unicorn 2.1.4, Python 3.12/3.14):
   ```bash
   python3 -m venv .venv-checker
   . .venv-checker/bin/activate
   pip install -r requirements-checker.txt
   python3 cells/gen_misfortune2.py      # writes cells/misfortune2.asm (Misfortune v3)
   python3 cells/check_cells.py --only misfortune2
   ```
   Omit `--only` to check all cells when `docs/cellhack.inc` or `check_cells.py` changes. The shelved VEX cells (`woe`, `conceit`, `endemic`) always fail as expected (`ALL OTHER CHECKS PASSED`, exit code 0); any other failure exits with code 1.

4. **Replay tools:** Replays are not in the repository. See "Doing your own pull" in [data-pulls.md](architecture/data-pulls.md). Each tool in `tools/replay/` requires `--pull <pull>`.
