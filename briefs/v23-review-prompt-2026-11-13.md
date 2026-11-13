Review the build brief `briefs/v23-brief-2026-11-13.md` for Bane v2.3 in the CellHack2 repo. Read-only: do not edit
files or run commands. Keep the reply under 600 words.

Context: `briefs/deep-review-2026-11-13.md` (the plan this brief implements), `cells/bane3.asm` (v2.3a, the base) and
`cells/gen_bane3.py` (its generator), `docs/cellhack.inc` (constants), `data/evidence-2026-11-12/m-r1-first-contact.txt`
and `m-solo-matrix.txt` (the evidence). Search first and read only the ranges you need.

Check, and answer each point with yes / no plus one or two lines:
1. Part A sketch: does it do what section 2 says on every path that reaches `rest:` in `cells/bane3.asm` (settled
   e < 5, threat e < 5, walker blocked, boxed, feed fallback)? Name any path where `al` is not what the sketch assumes.
2. Pitfalls 1-4: are they real, and is anything missing (for example the stored-bite byte layout `[2]` action,
   `[3]` view idx + 8; a stored bite toward a wall square; a child copying the new stored bite)?
3. Does any racing path (stored bite 4, first bite 12, refill 16, split 16, walker move 39, late split) change cost?
4. Tests: does each one fail on v2.3a and pass on v2.3? Is a test missing that would catch a wrong stored square?
5. Part B: is the acceptance rule (no flag t20-t60, at most -1% at t100, real cell within 1% of the sketch) enough to
   keep the opening from costing anything?
6. The after-upload targets: are they measurable with the named scripts, and are they the right ones to judge v2.3?

End with: ready to build (yes / no), and the list of fixes, most important first.
