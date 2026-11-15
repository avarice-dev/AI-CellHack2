# CellHack2: instructions for an agent that resumes this repository

**The project is likely done being updated.** It was a competition project: write x86-64 assembly "cells" for an online ladder, with a Python simulator and replay tools. The goal was a cell that takes #1 and holds it. It was not reached. The best cell, Misfortune v3 (cell 353), was #3 at the last check (2026-11-14 16:47, rating 1841; the leader Siect-F was at 2053). Do not start new work unless the owner asks.

## Where things are

- `README.md`: outcome, cell table, quick start.
- `architecture/overview.md`: glossary, repository layout, index of `reviews/` and `briefs/`.
- `architecture/cells-and-experiments.md`: lineage of every cell and the final ladder status.
- `reviews/final-round-2026-11-13-14.md`: the last round (Misfortune v2 failure, Depravity, Dogma NO-GO). Read it before any new design.
- `designs.md`: final state at the top, then the dated design rounds.
- `cells/` generators, assembly and `check_cells.py`. `sim/` simulator. `tools/` replay tools.
- `data/` is local only and not in the repository. Validation of the simulator needs it (see `architecture/data-pulls.md`).
- Tracking files (`planning.md`, `issues.md`, `tasks.md`) are local and git-ignored.

## Conventions to keep if someone resumes

- One bet per cell. Judge every idea against one question: does it make #1 more likely?
- State plainly how confident you are that a build takes and holds #1 before you build it. If you are not confident, say so and stop.
- Local pass bars only measure what the simulator can see. They do not show that a cell beats the live leader. Say so each time.
- Re-laddering a retired cell does not restore its rating. A new upload restarts the rating. Ask the owner before any ladder change.
- Before any upload: the checker (`cells/check_cells.py --only <cell>`, Unicorn diff with 0 mismatches), a read of the generated assembly, and a Sandbox game with 0 faults. A Sandbox loss against the previous version is a stop signal.
- Compare a change with the live version in paired, slot-balanced games. Do not use a control that already carries the change.
- Site requests: at least 15 seconds apart, replays at least 30 seconds apart, back off on an HTTP 429.
- Simulator runs may use 6 workers at normal priority. Run gates first and side checks after.
- Documents: architecture files and the README use Simplified Technical English. Use relative links, no absolute paths, no machine or account names, and "Claude" not model names. Run `python tools/privacy_check.py` before a commit. The repository is public. Never push without the owner's approval.
- Commit trailer: `Co-Authored-By: Claude <noreply@anthropic.com>`.
