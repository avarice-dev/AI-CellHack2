# Misfortune v2 (`cell 352`) Consolidated 8-Agent Audit & Execution Plan

**Date:** 2026-11-14  
**Scope:** End-to-end audit of `Misfortune` / `Misfortune v2` (`AC1` failure post-mortem, `split10` hotfix verification, replay diagnosis vs `#1 Siect-F` / `VarSi` / `Colossus`, devil's-advocate kills, surviving levers, harness/checker bugs, and pre-registered execution gates).

---

## 0. Immediate Executive Directive for Claude Code (Read First on Reset)

- **Live `cell 352` status (`make_misfortune2_split10`, UNCOMMITTED):** [`cells/gen_misfortune2.py`](../cells/gen_misfortune2.py) -> [`cells/misfortune2.asm`](../cells/misfortune2.asm) (`43,273 B` source / `23,674 B` binary) is **`v1 + hold='split' (hold_min=10)`** (`armed 2`, `arm 19`, `Gate 1 = 15`, `cap B 80`, `3/3` `0x67` prefixes, `0` `rsi`-mem; [`cells/check_cells.py`](../cells/check_cells.py) `--only misfortune2` passed **`59,058` Unicorn cases, `0` mismatches**, [`REVIEW.md`](final-round-2026-11-13-14.md)). User observed live `split10` pushed back `Siect-F` better than `AC1`.
- **HARD FREEZE on `cell 352`:** Do **NOT** modify or re-upload live `cell 352` unless an isolated single-factor variant clears the full **Phase 2 Ship Gate** (`L1 + calibrated L2`, `16` seeds, `3000t`, `pfc == 0`, Unicorn `0` mismatches, Sandbox `0` faults, post-upload replay diff).
- **Mandatory Process Rules:**
  1. **ZERO bundled commits:** 1 isolated change per ablation and commit (`T_EARLY` alone, `T_FEED` alone, etc.).
  2. **Commit baseline first:** Commit the `split10` hotfix baseline cleanly before any new experiment (after Phase 0 fixes; keep the untracked earlier research briefs out of technique commits if embargoed).
  3. **Phase 0 before any strategy sim:** Fix the broken runner/unit-test/checker bugs and build calibrated `L2` rivals (`Siect-F`, `VarSi`, `Colossus`) in [`sim/rivals.py`](../sim/rivals.py) + [`sim/validate.py`](../sim/validate.py) **before** running any Phase 1 ablation.
  4. **Respect `git push` embargo:** [`planning.md`](../planning.md#L43) blocks remote pushes via `git config remote.origin.pushurl`; do **not** unset or push without explicit user approval. Follow [`CLAUDE.md`](../CLAUDE.md) (`6` workers, normal priority, ~20-min batches, state confidence before builds, local != ladder).

---

## 1. Post-Mortem: Why `AC1` (`b40b1a4`) Failed & How Claude Let Bugs Slip

`AC1` (`b40b1a4`, deployed to `cell 352` before the `split10` hotfix) bundled four interacting changes that masked each other in local tests and hurt real ladder performance:

1. **Checked refill (`refill='checked'`):**
   - Slowed `arm:` first bite from `19 -> 22 / 26 / 28` insns (`22` clean, `26` square taken, `28` `e < 12`, [`2026-11-13_asm-check_misfortune2.md`](../briefs/misfortune2-asm-check-2026-11-13.md)) and slowed Gate 1 non-fire refills/splits from `15 -> 20-39+` (`23..66` across sweep paths, flipping early `t=15` scan races on `s2`: `m2v0` `566/609` vs `split10` `775/989`, [`REVIEW.md`](final-round-2026-11-13-14.md)).
   - Exploded unintended friendly bites (`armed_friend`) by **`+115-120%`** vs `split10`: in `hold-off` (`8` seeds, `3000t`), `split10` had `af = 17,033` (`1.22/100`), whereas in `ac1-gate3000` (`8` seeds, `3000t`) `m2v0` jumped to `af = 36,655` (`2.66/100`, `62.5%` `on_rch = 22,922`) and `ac1` hit `af = 37,475` (`2.63/100`, **`73.9%`** `on_rch = 27,702`). In `ac1-screen` (`8` seeds, `1000t`), `on_rch` was `68.3%` (`10,769/15,759`) for `m2v0` and `77.7%` (`12,108/15,575`) for `ac1`.
2. **`hold='off'` (`hold_min=5`):**
   - Replaced clean diagonal holds (`<10`) / immediate splits (`>=10`) with rotating walker dispersal on `5..9` front cells (`REVIEW.md:40`), nearly doubling early deaths (`d100 = 151.1` vs `84.5` base and `81.1` `split10` in [`hold-off-2026-11-13.md`](../sim/out/hold-off-2026-11-13.md#L24-L28)) and failing the `3000t` paired gate (`5/8`, while `split10` passed `7/8`).
3. **Armed children (`e & 3 == 1`) + conditional `FEED_PAD=6`:**
   - In `ac1-screen`, `seed 6` hit `pfc=1` at `t=71->72, (45, 24), e=4` (`pfc_events=[[72, 45, 24, 4, 49]]`): a neighbor ran Schism `ACT_FEED` (`94..96` insns) **before** an `e=5` dispersal `emit` (`97` insns), bumping `5 -> 7` before `ACT_SPLIT` executed, producing `child=3` and **`parent=4`** (even, firing armed child slot `4` at `n=2` on its own newborn, [`PLAN.md`](final-round-2026-11-13-14.md)).
   - `MISFORTUNE_FEED_PAD = 6` pushed `feed` to `100+` (`split/95/0 < feed/100/0` vs `feed/94/96`), leaving safety **conditional** on keeping every future `emit` path `< 100` insns.
4. **Why metrics fooled Claude:**
   - **Broken `L1` benchmark:** [`sim/misfortune_runner.py`](../sim/misfortune_runner.py#L33) tests only our 4 own legacy cells (`bane22, conviction, penalty` + `ctrl` `v2.3a`), with zero `Siect-F`, `VarSi`, or `Colossus` proxies.
   - **Confounded controls & small `n`:** `ac0` ran only `n=1` in the killed [`armed-children-v2`](../data/shared-2026-11-13/2026-11-13_2317_armed-children-v2_games.jsonl) batch (`93.3%` `on_rch = 4,817/5,160`); `kid_alive10_armed < kid_alive10_unarmed` (`0.681 vs 0.700` on `ac1 s1`) was a seed-1 artifact (`ac1-screen` `n=8` had `531/772 = 68.8%` vs `375/620 = 60.5%`, `7/8` seeds); and `ac1-gate3000` compared `ac1` against `m2v0` (which already carried the checked-refill `af` regression) rather than `split10`.
   - **Ignored live warning:** Sandbox `148415` lost **`63 vs v1 111`** ([`data/site-checks.md`](../data/site-checks.md#L20)), yet `AC1` was laddered anyway before `ac1-gate3000` finished.

---

## 2. Empirical Diagnosis: `Misfortune (split10)` vs `#1 Siect-F` and Rivals

### Priority 1 — `t30 -> t100` Expansion Deficit (Primary Bottleneck)
In equal-area game `147569` (`765` vs `777` Voronoi area, [`data/siectf-growth-2026-11-13.md`](../data/siectf-growth-2026-11-13.md#L44)), `Misfortune` **led at `t30` (`161 vs 116`)**, then fell behind **`711 vs 960` (`t60`)** and **`1125 vs 1835` (`t100`)** long before late-game `300+` combat. Three mechanisms drive this gap (measured in [`docs/evidence/bane-v22-evidence-2026-11-12.md`](../docs/evidence/bane-v22-evidence-2026-11-12.md), [`m2-varsi-budget.txt`](../data/evidence-2026-11-12/m2-varsi-budget.txt), [`m2b-far-none.txt`](../data/evidence-2026-11-12/m2b-far-none.txt), [`budget-summary.txt`](../data/evidence-2026-11-12/budget-summary.txt)):
1. **`near+front` stall (partially addressed by `split10`):** In window `b` (`t30-60`), `v2.2`'s `near+front` open `e>=5` split rate was **`28.7%` vs `VarSi 58.1%`** (`5` eq-start losses pooled, `m2-varsi-budget.txt:103`) and **`32.9%` vs `Colossus 56.9%`** (`3` losses pooled, `m2-varsi-budget.txt:249`). `split10` relieves `e >= 10` diagonal stalls (`+7%` final locally), leaving `e = 5..9` holds intact.
2. **`far` self-collisions:** In window `b`, real `far` open `e>=5` no-event rate was **`18.6%`** vs solo **`18.4%`** (`m2b-far-none.txt:3,17`), showing early dispersion collides internally at the same rate as solo play.
3. **Heavy early/mid interior feeding:** `Bane/Misfortune` spends **`14.0%`** (`t60-100`) and **`44.4%`** (`t100-200`) of cell-ticks feeding (`budget-summary.txt:17,21`, plus `5.6%` at `t30-60`), whereas `Siect-F` and `VarSi` feed **`0.0%`** (`bane-v22-evidence-2026-11-12.md:237-238`). *(Exception: `Colossus` feeds `16.4% / 50.6% / 56.1%` in `a/b/c` and immediately bites refill children at **`94.0%`** on tick 1 (`bane-v22-evidence-2026-11-12.md:239,371`), proving anti-Colossus robustness must be tested if cutting early feed.)*

### Priority 2 — Sustained Contact & Conversion Deficit (`146477` & `Cap B`)
In `146477` (`674` vs `1161` area, [`data/siectf-games.md`](../data/siectf-games.md#L2)), `Misfortune` won **`89%`** bitten-first at `300+` (`172,800` ticks; `87%` at `100-300`, `71%` at `<100`), yet still lost `freed_S_cell` conversions (**`154` `M` vs `226` `S`**) and ended **`787 vs 3309`**. Root causes from Stage 2/3 ([`stage2-report.md`](../sim/out/misfortune/stage2-report.md), [`stage3-report.md`](../sim/out/misfortune/stage3-report.md)):
1. **`19`-insn `arm:` vulnerability (`15.2%` of contacts):** In Stage 2 (`B1`), `242,477 / 1,596,577 = 15.2%` of contact calls were `arming/19/1` (vs `1,354,100` `armed/2/1`), which loses ~100% of first-bite and rescan races against `Siect-F` (`<=3`) and `VarSi` (`4..15`).
2. **`e=50` parity miss (`11.7%` at `1000+`) & `k=0` at `te <= 2`:** `B1` contacts hit `e=50` on **`11.7%`** of `1000+` calls (`23.9%` at `e=49`), dropping slot coverage to the parity gap; `exact=1` sets `k=0` at `te <= 2`, clearing slots on kill ticks and giving up **`~4.4pp`** vs `B0` against `bane22` (`88.6%` vs `93.0%` at `1000t`, `stage1`/`stage3`).
3. **Irreducible `Cap B` `~53k-57k` (`~3.8-4.2%`) `af + afail` floor:** Stage 2 had `25,892` `armed_friend` + `34,831` `armed_fail` (`60,723 / 1,596,577 = 3.80%` of all contacts; `>= 84.8%` of `af + afail` is on `con=1` active combat fronts in `B1` vs `>= 82.0%` in `split10`, since `con == 0` has only `9,253` / `10,228` calls), and `28,081` stuck episodes (`70.0%` ended by `enemy_refill`, `21.9%` `feed`, `4.3%` `friend_refill`).
4. **Why `Siect-F` converts despite losing `89%` bitten-first:** `Siect-F` matches `15`-insn refills (`182 vs 162` in `147122/146477` `window.refill`, `siectf-growth-2026-11-13.md:31`), switches targets cleanly on kill (**`84.8%`** self-kill / **`89.1%`** other-kill, vs Conviction's `9.1% / 4.7%`, `bane-v22-evidence-2026-11-12.md:370,373`), and survives at `1-2` energy (**`76.8%` / `77%`** `alive10` vs Bane `28%`, `bane-v22-evidence-2026-11-12.md:186,190`) because `2`-energy children resist `19`-insn rescans.

---

## 3. Proven Dead-Ends & Rejected Designs (Do NOT Re-Test)

| Rejected Idea | Exact Empirical / Mathematical Disqualification | Source |
|---|---|---|
| **`donor <= 48` pull skip** | In Stage 2 (`B1`), `1,241,225` pulls occurred with `>=82%` of high-energy contacts at `e >= 47` and `>=81-87%` of pulls driven by `e=49/50` donors; skipping `donor <= 48` disables ~85-90%+ of `Cap B` pulls, causing `Cap N` collapse (`52.0%` bit-first vs `bane22`, `53.3%` vs `conviction`, `8.81/100` `af`). The `2,033,998` `pull_cap_loss` is boxed interior overflow, **not** front colony drain. | [`stage1n-report.md`](../sim/out/misfortune/stage1n-report.md), [`stage2-report.md`](../sim/out/misfortune/stage2-report.md#L27) |
| **`slot 50` at `e0 >= 49` / `.keep50` (`Cap A`)** | Forces front cells to hold at `e=50`, failing Stage 1 with **`6.63%`** stuck (`14,070` fails / `212,290` contacts) and **`-379` net cells** vs control (`A1` `s1-4`). Also adds `+2` insns to `arm:`. | [`stage1-report.md`](../sim/out/misfortune/stage1-report.md#L23,L39) |
| **`VLock-4`** (`4`-insn view-checked bite, `13`-insn `arm`, `Gate 1=17`) | **KILLED by Agent 7 Devil's Advocate:** Empirically identical to `Bane v2.2`'s `4`-insn checked lock, which went **`0/3` vs `Siect-F`** (`0.0% vs 99.8%` `B armed` stun lock in `bane-v22-evidence-2026-11-12.md:341`), losing **100%** of locked exchanges against `<=3` `Siect-F` while `13`-insn `arm` + `17`-insn checked refill also lose to `4..15` `VarSi`/`Colossus`. **Zero ASM time permitted** *(optional Python-only negative control in Phase 1B at most)*. | [`bane-v22-evidence-2026-11-12.md`](../docs/evidence/bane-v22-evidence-2026-11-12.md#L341) |
| **`checked refill` on blind slots (`m2v0`/`AC1`)** | Slows `arm:` `19 -> 22/26/28` and `Gate 1` `15 -> 20-39+`; explodes `armed_friend` **`+115-120%`** via `62.5-73.9%` `on_rch`. | [`REVIEW.md`](final-round-2026-11-13-14.md) |
| **`hold='off'` (`hold_min=5`)** | Doubles early deaths (`d100 = 151.1` vs `81.1` `split10`) and fails `3000t` paired gate (`5/8`). | [`hold-off-2026-11-13.md`](../sim/out/hold-off-2026-11-13.md#L35-L41) |
| **`open-long 16/2 sparse-stop 4`** | Loses **`-30%`** at `t20` on two corner squares and `-0.7%` to `-4.8%` at `t100`; `popcnt` is **illegal** (faults on site `103568`). | [`deep-review-2026-11-13.md`](../briefs/deep-review-2026-11-13.md#L76-L78), [`site-observations-2026-11-08.md`](../docs/evidence/site-observations-2026-11-08.md#L34) |
| **`exact=0` (`B0`)** | `4.13/100` `af`, `3.3%` stuck (`1000t`, `s1-2`), no empty-square cut-off. | [`stage3-report.md`](../sim/out/misfortune/stage3-report.md#L18) |
| **`growth-gates` `threat_min=5` (`m2v2`/`m2v3`)** | Gate 1 is not enemy-gated (`cells_ref.py:143`); sets `moves = 0` and collapses to `~533` (`464-548`) cells. | [`REVIEW.md`](final-round-2026-11-13-14.md) |

---

## 4. Surviving Candidates & Exact ASM / Timing Engineering Specs

1. **`T_EARLY > 0` (`+0` insns, `+0 B` — HIGHEST-PRIORITY FREE TEST):**
   - **Location:** [`cells/misfortune2.asm:106`](../cells/misfortune2.asm#L106) (`emit:` -> `cmp dword [rdi + VIEW_TICK], 0 / jb emit_long`).
   - **Mechanism:** Changing `0` to `T_EARLY` (test `20, 30, 45, 60`) sends `8`-step walkers on **all** non-first-from-square splits before `T_EARLY` instead of `2`-step walkers, attacking `t30->t100` early dispersion / `far` self-collisions at **zero instruction or byte cost**.

2. **`T_FEED` (`+2` insns, `+10 B` — HIGH-PRIORITY `t30->t100` TEST):**
   - **Location:** [`cells/misfortune2.asm:180`](../cells/misfortune2.asm#L180) (right before Schism `5x5` / empty-edge feed, leaving `cap B` hold/lift above `180` untouched).
   - **Variants to test decoupled:**
     - **Option T1 (`jb fallback`):** Skip `e=6..15` Schism boxed feeding before `T_FEED`, keeping `e >= 16` `fallback:` feeding (`L218`).
     - **Option T2 (`jb rest`):** Skip all boxed non-cap feeding before `T_FEED` (matching `Siect-F`/`VarSi` `0.0%` early feed).
   - **Trade-off watch:** Must verify against `Colossus` (which feeds heavily `a/b/c` and bites refills `94.0%`) and on corner/boxed starts in the 11-start solo matrix.

3. **`arm_tbl` (`arm: 19 -> 17` insns, `-394 B` net — LOW-CEILING CLEANUP ONLY):**
   - Optimal lower bound for `exact=1 cap-B arm:` (folding `row_tbl` + `shl edx, 4` at [`misfortune2.asm:138-139`](../cells/misfortune2.asm#L138-L139) into indirect `jmp [arm_tbl + ...]` / 4 directional stubs).
   - Requires `256`-entry tables (or `and edx, 63`) and `FF 24 C5` + jump-target checks in `check_cells.py`. Low ELO ceiling (still loses to `<=3` `Siect-F` and `4..15` `VarSi` UP/DOWN); only pursue if free after macro levers.

4. **`emit`-only `armed_children` (`FEED_PAD = 0`, DECOUPLED NEGATIVE/SKEPTICAL TEST):**
   - Without `checked_refill`, `max(armed emit)` is `82..85` insns `< 92 = min(Schism ACT_FEED)` (removing `FEED_PAD=6` entirely).
   - **Why skeptical:** `Gate 1` (`e >= 16`, `kRefill` `6..21`) + `hold_split` (`e=10..15` diagonals) leave `emit` mainly covering `e in {5, 9}` at axis-far `{2, 10, 14, 22}` and `e=13` at `{2, 22}`, while taxing open `emit` `+2..+15` insns. (`hold_split` child arming slows `29 -> 45` insns — avoid.) Test isolated on `L1 + L2` only if `T_EARLY`/`T_FEED` leave room.

5. **`first 8/2 dir-open` (`emptiest side` without `popcnt`, `+2,084 B`):**
   - Solo curve gain is modest (`+4.9%` `t60` [`1063 -> 1115`], `+2.4%` `t100` [`2942 -> 3012`], [`deep-review-2026-11-13.md`](../briefs/deep-review-2026-11-13.md#L74-L75)), slows `settled:` splits to `105-128` insns, clobbers `ecx` (`VIEW_X`) unless carefully routed, and **MUST NEVER** be paired with `armed_children` (would push `emit > 128`, forcing `FEED_PAD = 37` and slowing feeds to `129..162+` insns). Prefer `T_EARLY` / cheaper dispersion tweaks first.

6. **Structural Open Question (Only If Phase 1 Macro Levers Aren't Enough):**
   - Whether a fundamentally faster `<= 3`-insn semi-checked or `queue3`-style architecture (`3 / 16` gave `+12.0/+10.8` first-order flip vs `Siect-F` in [`bane-v22-evidence-2026-11-12.md`](../docs/evidence/bane-v22-evidence-2026-11-12.md#L421), vs `2`-insn `exact=1` + `17-19`-insn `arm:`) is needed to hold `#1` against `Siect-F`.

---

## 5. Harness, Simulator, Checker & Git Bugs Requiring Phase 0 Fixes

1. **`sim/misfortune_runner.py` & `sim/tests/test_misfortune_runner.py`:**
   - [`sim/misfortune_runner.py:128`](../sim/misfortune_runner.py#L128) hardcodes `misfortune_cap_rule(view, 'B')` -> change `'B'` to `getattr(self.sub, 'cap', 'B')`.
   - [`sim/misfortune_runner.py:108`](../sim/misfortune_runner.py#L108) hardcodes `r[1] == 2` -> change to `self.armed_n`.
   - [`sim/tests/test_misfortune_runner.py:121-128`](../sim/tests/test_misfortune_runner.py#L121-L128): `test_pull_counts_and_cap_loss` places friend `(2, 2)` at `e=30` with no enemy on its ring, so `misfortune_cap_rule(view, 'B')` returns `None` and `r['pulls'] == 0` fails the assertion. Fix fixture (`en >= 48` + enemy on `(2, 2)`'s ring for pull, `en >= 47` + empty edge & no enemy for lift).
2. **`sim/tests/test_armed_children.py`:**
   - [`sim/tests/test_armed_children.py:5-6, 95-96`](../sim/tests/test_armed_children.py#L5-L6) claims parent energy stays odd after any run of bites/feeds and failed splits. That invariant is **false** whenever an earlier-turn neighbor runs `ACT_FEED` before `ACT_SPLIT` on the same tick (`s6 t=71->72 pfc=1`). Fix docstring/assertions and add a real `engine.py` integration test for same-tick `ACT_FEED < ACT_SPLIT`.
3. **`sim/cells_ref.py`:**
   - [`sim/cells_ref.py:969-986, 1019`](../sim/cells_ref.py#L969-L986): `make_misfortune2()` and `FACTORIES['misfortune2']` still point to unshipped `m2v0` (`refill='checked'`) instead of `make_misfortune2_split10()`.
   - [`sim/cells_ref.py:965`](../sim/cells_ref.py#L965): `make_misfortune()` does not set `misfortune.refill = refill` (only `make_misfortune2()` sets `p.refill`).
4. **`sim/hold_off_runner.py`, `sim/rivals.py`, `sim/validate.py`:**
   - [`sim/hold_off_runner.py:10-28`](../sim/hold_off_runner.py#L10-L28) retains broken `m2v2`/`m2v3` (`threat_min=5`), lacks `split10` in `M2` and decoupled variant flags (`t_early`, `t_feed`).
   - [`sim/rivals.py`](../sim/rivals.py) and [`sim/validate.py:39-61`](../sim/validate.py#L39-L61) lack calibrated `L2` models for **`Siect-F`**, **`VarSi`**, and **`Colossus`**.
5. **`cells/check_cells.py`:**
   - [`cells/check_cells.py:802`](../cells/check_cells.py#L802) hardcodes `v2 = False`; `_mis_view` (`L766`) only samples `te` in `1..50` (missing OOB `te` `51..255` guard check); add `arm_tbl` `FF 24 C5`/target check if `arm_tbl` is ever built.
6. **Uncommitted Working Tree:**
   - Modified: `cells/check_cells.py`, `cells/gen_misfortune2.py`, `cells/misfortune2.asm`, `sim/cells_ref.py`. Untracked: three earlier research briefs/reports from 2026-11-12 (not part of the commit).

---

## 6. Pre-Registered Phase 0 / Phase 1 / Phase 2 Action Plan & Stop/Go Gates

| Phase | Scope & Exact Work | Pass / Stop-Go Gate |
|---|---|---|
| **Phase 0: Fix & Calibrate** *(before any sim)* | 1. Fix `misfortune_runner.py:108,128`, `test_misfortune_runner.py:121-128`, `test_armed_children.py:5-6,95-96`, `cells_ref.py:965,969-986,1019`, `hold_off_runner.py:10-28`, `check_cells.py:766,802`.<br>2. Commit clean `split10` baseline + Phase 0 fixes (respect `git push` embargo).<br>3. Build & calibrate **`L2` rivals** (`Siect-F`, `VarSi`, `Colossus`) in `rivals.py` + `validate.py` against replay fingerprints (`data/pull*`). | `unittest` 100% green; `check_cells.py --only misfortune2` `0` mismatches; `L2` rivals match replay `t60`/`t100`, `fpe`, bite-cost tier, and refill-bite behavior. |
| **Phase 1A: 11-Start Solo Matrix** | Test isolated **`T_EARLY`** (`20, 30, 45, 60`) and **`T_FEED`** (`T1`/`T2`, thresholds `45, 60, 80, 100`) vs `split10` on the 11 sampled start squares (center, edge, corner). | **Pass:** strictly `>= -1%` on every corner/bad start at `t20..t100` and net positive median `t60`/`t100` vs `split10`. Reject any corner regression. |
| **Phase 1B: `1000t` Decoupled Screen (`L1 + L2`)** | Run surviving single-factor `T_EARLY`, `T_FEED`, and (optionally) `emit`-only `armed_children` (`FEED_PAD=0`) on **8 seeds × 1000t** vs both `L1` (`bane22, conviction, penalty`) and `L2` (`Siect-F, VarSi, Colossus`). | **Advance to Phase 2:** beats paired `split10` on `>= 6/8` seeds in `L2` (and no `L1` collapse), `pfc == 0`, improved equal-start `t60`/`t100` vs `Siect-F`/`VarSi`, no `Colossus` regression. |
| **Phase 2: Ship Gate** | **16 seeds × 3000t** paired (`L1 + L2`) vs `split10` (`RAISE_PARENT_FIRED = True`), full NASM + Unicorn check (`check_cells.py --only misfortune2`, `0` mismatches, `ALLOWED` ISA only), planted-mutation check, Sandbox `0` faults, then post-upload replay diff (`>= 25` games / `siectf_probe.js`). | **Ship `cell 352` ONLY IF:** `>= 12/16` (`>= 6/8` per half) vs `split10` on `L2` and `L1`, **`pfc == 0`**, `0` Unicorn mismatches, `0` Sandbox faults. **Rollback rule:** if `0`-fault Sandbox loses badly or first ~25-50 ladder games regress vs `split10` (`t60`, area conversion, `Siect-F` share), revert to committed `split10`. |
