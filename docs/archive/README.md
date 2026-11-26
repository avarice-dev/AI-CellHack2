# Historical Documentation Archive (2026-11-07 to 2026-11-14)

This directory preserves substantive historical design notes, reviews, specs, and build-check records from the CellHack2 project (`2026-11-07` through `2026-11-14`). These documents are **historical records**—not canonical current documentation.

For current, canonical documentation, see:

- [`README.md`](../../README.md) — project entry point, quick start, and layout
- [`architecture/overview.md`](../../architecture/overview.md) — game overview, outcomes, glossary, and repository layout
- [`architecture/cells-and-experiments.md`](../../architecture/cells-and-experiments.md) — cell progression and final ladder status
- [`architecture/cell-assembly.md`](../../architecture/cell-assembly.md) — x86-64 NASM cell engineering
- [`architecture/simulator.md`](../../architecture/simulator.md) — local Python simulator
- [`architecture/data-pulls.md`](../../architecture/data-pulls.md) — ladder data pulls and local-only `data/` layout
- [`sim/README.md`](../../sim/README.md) — simulator usage and test suites

> **Note on inline source comments:** Historical comments in `cells/*.py`, `cells/*.asm`, and `sim/*.py` still cite the legacy root paths (`designs.md`, `reviews/...`, `briefs/...`). Use the legacy-path mapping below to locate the archived files. Paths under `data/` and `sim/out/` mentioned inside archived files refer to local working data not committed to the repository (see [`architecture/data-pulls.md`](../../architecture/data-pulls.md)).

## Archive Index

### Design Notes

- [`designs.md`](designs.md) — CellHack2 cell designs: final-state summary (2026-11-14) followed by dated rounds 1–11.

### Reviews (`reviews/`)

| Archived File | Description |
| --- | --- |
| [`reviews/final-round-2026-11-13-14.md`](reviews/final-round-2026-11-13-14.md) | Final round (2026-11-13 to 2026-11-14): decisions, measurements, Depravity live failure, Dogma gauntlet, and verdicts. |
| [`reviews/dogma-clean-sheet-review-2026-11-14.md`](reviews/dogma-clean-sheet-review-2026-11-14.md) | Clean-sheet strategic review and final specification for `Dogma` (2026-11-14). |
| [`reviews/misfortune2-audit-2026-11-13.md`](reviews/misfortune2-audit-2026-11-13.md) | Consolidated 8-agent audit and post-mortem of Misfortune v2 (`cell 352`) and dead ends (2026-11-13). |
| [`reviews/decisions-r1.md`](reviews/decisions-r1.md) | Round 1 decisions (2026-11-07). |
| [`reviews/r1-asm.md`](reviews/r1-asm.md) | Round 1 review: assembly feasibility and instruction-count engineering. |
| [`reviews/r1-rules.md`](reviews/r1-rules.md) | Round 1 review: rules accuracy and exploits. |
| [`reviews/r1-strategy.md`](reviews/r1-strategy.md) | Round 1 review: strategy. |
| [`reviews/r2-review.md`](reviews/r2-review.md) | Round 2 review. |
| [`reviews/r3-review.md`](reviews/r3-review.md) | Round 3 review against ladder pulls 1 and 2 (2026-11-08). |

### Briefs & Specs (`briefs/`)

| Archived File | Description |
| --- | --- |
| [`briefs/contact-brief-2026-11-10.md`](briefs/contact-brief-2026-11-10.md) | Contact study of new rivals and plan for Bane v1 and v2 (2026-11-10). |
| [`briefs/deep-review-2026-11-13.md`](briefs/deep-review-2026-11-13.md) | Deep review of Bane v2.2 measurements and path forward (2026-11-13). |
| [`briefs/v23-brief-2026-11-13.md`](briefs/v23-brief-2026-11-13.md) | Build plan for Bane v2.3 (2026-11-13). |
| [`briefs/misfortune-spec-2026-11-13.md`](briefs/misfortune-spec-2026-11-13.md) | Final specification and test plan for Misfortune (2026-11-13). |
| [`briefs/misfortune-build-review-2026-11-13.md`](briefs/misfortune-build-review-2026-11-13.md) | Misfortune build review and sign-off pack (2026-11-13). |
| [`briefs/misfortune-asm-check-2026-11-13.md`](briefs/misfortune-asm-check-2026-11-13.md) | Misfortune v1 assembly check (cap B, exact 1) (2026-11-13). |
| [`briefs/misfortune2-asm-check-2026-11-13.md`](briefs/misfortune2-asm-check-2026-11-13.md) | Misfortune v2 assembly check (2026-11-13). |
| [`briefs/misfortune-byte-dumps-2026-11-13.txt`](briefs/misfortune-byte-dumps-2026-11-13.txt) | Hex memory byte dumps (bytes 0–63) for the Misfortune build (2026-11-13). |

## Legacy-Path Mapping

| Legacy Path | Current Status / Location |
| --- | --- |
| `designs.md` | [`docs/archive/designs.md`](designs.md) |
| `reviews/decisions-r1.md` | [`docs/archive/reviews/decisions-r1.md`](reviews/decisions-r1.md) |
| `reviews/dogma-clean-sheet-review-2026-11-14.md` | [`docs/archive/reviews/dogma-clean-sheet-review-2026-11-14.md`](reviews/dogma-clean-sheet-review-2026-11-14.md) |
| `reviews/final-round-2026-11-13-14.md` | [`docs/archive/reviews/final-round-2026-11-13-14.md`](reviews/final-round-2026-11-13-14.md) |
| `reviews/misfortune2-audit-2026-11-13.md` | [`docs/archive/reviews/misfortune2-audit-2026-11-13.md`](reviews/misfortune2-audit-2026-11-13.md) |
| `reviews/r1-asm.md` | [`docs/archive/reviews/r1-asm.md`](reviews/r1-asm.md) |
| `reviews/r1-rules.md` | [`docs/archive/reviews/r1-rules.md`](reviews/r1-rules.md) |
| `reviews/r1-strategy.md` | [`docs/archive/reviews/r1-strategy.md`](reviews/r1-strategy.md) |
| `reviews/r2-review.md` | [`docs/archive/reviews/r2-review.md`](reviews/r2-review.md) |
| `reviews/r3-review.md` | [`docs/archive/reviews/r3-review.md`](reviews/r3-review.md) |
| `briefs/contact-brief-2026-11-10.md` | [`docs/archive/briefs/contact-brief-2026-11-10.md`](briefs/contact-brief-2026-11-10.md) |
| `briefs/deep-review-2026-11-13.md` | [`docs/archive/briefs/deep-review-2026-11-13.md`](briefs/deep-review-2026-11-13.md) |
| `briefs/misfortune2-asm-check-2026-11-13.md` | [`docs/archive/briefs/misfortune2-asm-check-2026-11-13.md`](briefs/misfortune2-asm-check-2026-11-13.md) |
| `briefs/misfortune-asm-check-2026-11-13.md` | [`docs/archive/briefs/misfortune-asm-check-2026-11-13.md`](briefs/misfortune-asm-check-2026-11-13.md) |
| `briefs/misfortune-build-review-2026-11-13.md` | [`docs/archive/briefs/misfortune-build-review-2026-11-13.md`](briefs/misfortune-build-review-2026-11-13.md) |
| `briefs/misfortune-byte-dumps-2026-11-13.txt` | [`docs/archive/briefs/misfortune-byte-dumps-2026-11-13.txt`](briefs/misfortune-byte-dumps-2026-11-13.txt) |
| `briefs/misfortune-spec-2026-11-13.md` | [`docs/archive/briefs/misfortune-spec-2026-11-13.md`](briefs/misfortune-spec-2026-11-13.md) |
| `briefs/v23-brief-2026-11-13.md` | [`docs/archive/briefs/v23-brief-2026-11-13.md`](briefs/v23-brief-2026-11-13.md) |
| `reviews/designs-r1-snapshot.md` | Removed from `HEAD` (ephemeral snapshot; available in git history) |
| `reviews/designs-r2-snapshot.md` | Removed from `HEAD` (ephemeral snapshot; available in git history) |
| `reviews/designs-r3-snapshot.md` | Removed from `HEAD` (ephemeral snapshot; available in git history) |
| `briefs/resume-2026-11-10.md` | Removed from `HEAD` (ephemeral session handoff; available in git history) |
| `briefs/resume-2026-11-11.md` | Removed from `HEAD` (ephemeral session handoff; available in git history) |
| `briefs/v23-review-prompt-2026-11-13.md` | Removed from `HEAD` (ephemeral review prompt; available in git history) |
