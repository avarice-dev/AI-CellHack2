# CellHack2 Clean-Sheet Strategic Review & Final Specification: `Dogma`

> Note (2026-11-14, added in the documentation review): historical. Dogma was built to this specification. It met every count but did not beat Misfortune v3 on the local engine, so it was never uploaded (NO-GO). The standings quoted here are from the time of writing. See [final-round-2026-11-13-14.md](final-round-2026-11-13-14.md).

**Date:** 2026-11-14  
**Scope:** Strictly read-only synthesis of full cell lineage, decoded ladder replays, live site standings, x86-64 ABI v4 / Ruleset v9 boundaries, red-team elimination, and converged clean-sheet specification for overtaking `#1 CogSpore-Siect-F (1962)`.  
**Primary Sources Verified:** `docs/cellhack.inc`, `cells/check_cells.py`, `sim/engine.py`, `cells/gen_scourge.py`, `cells/gen_schism.py`, `cells/gen_bane2.py`, `cells/gen_conviction.py`, `cells/gen_penalty.py`, `cells/gen_misfortune.py`, `cells/gen_misfortune2.py`, `cells/depravity.asm`, `data/site-checks.md`, `data/opening-search-2026-11-11.md`, `data/siectf-growth-2026-11-13.md`, `data/siectf-games.md`, `docs/evidence/bane-v22-evidence-2026-11-12.md`, `briefs/deep-review-2026-11-13.md`, `data/evidence-2026-11-12/*`, and `issues.md`.

---

## 1. Executive Summary & Top-Level Verdict

### Top-Level Verdict
1. **Abandon `C1` (`2`-insn `e`-slot) & `Depravity` (`363`) — Neither Can Cleanly Overtake `1962`:**
   - **Live `Depravity` (`cell 363`, `6cfb4a7`)** is structurally broken on the ladder despite finishing 1st (`138 vs 33`) in small-board `16x16` Sandbox `151538`. Dropping Cap B creates a deterministic `48 <-> 50` front stalemate (`e=50` drops to `17`-insn `arm:`, gets stunned back to `48`, bites at `2` insns back to `50` forever), `T_FEED=200` starves `t60–t199` battlefronts, `HOLD_MIN=8` spawns suicidal `4e` children while holding `5–7`, and `dir-open` taxes every settled split `76–139` insns.
   - **Any `C1` (`2`-insn `e`-slot) architecture is REJECTED (`REJECT`):** Even with unpadded `49`-insn Cap B and Stage 4 pre-arms stripped (whose pre-arms contain fatal `t_failed_eat` infinite air-bite loops and `e0` prefix-wipe / `+1,-2` parity mismatches), `m11-contact-stats.txt` proves **`52.3%`** of contact ticks have `>= 2` enemies (causing `4.5` blind friendly bites per `100` enemy bites, `82%` at `e <= 47` outside Cap B), **`92.3% (a)` / `38.1% (b)`** of kills lack a boxed `>= 6e` edge friend (leaving unbacked spearheads in `48 <-> 50` locks), and Cap B burned `90,384` energy over `52,620` pulls (`1.7e/pull`, `issues.md:8`).
2. **Converge on a Single Clean-Sheet Primary Target: `Dogma` (`C3b` Calibrated + `first 8/2`):**
   - **Combat (`3` / `15` insns):** `C3b` bitmask shift counter (`shr qword [rdx+8], 1 / mov al, [rdx+16] / jnz EXIT_ADDR`) with `1`-insn cleanup (`xor eax, eax`), **`15`-insn `arm:`**, and **`15`-insn `Gate-1`** (`REFILL_MIN=12`, `THREAT_MIN=16`). Eliminates the `e=50` cliff and `Cap B` burn completely, supports up to `63` consecutive bites (`0` mid-duel re-scans), bounds crossfire/KS blind tails via **`K_CAP = 16`** (`k(1..2) = 1` exploiting `RULESET_VERSION=9`'s verified `stun_keeps_memory=True` from `m9-stun-memory.txt:4`), and avoids `C3a`'s 8th-tick leak (`1` re-arm / `17` ticks vs `1` / `8`).
   - **Opening (`t0–t100`) & Macro:** Restores proven **`first 8/2`** dispersal in `MEM[0..7]` (`0/11` solo regressions, `t100 = 3012` in `opening-search-2026-11-11.md:14`, fixing `(0,0)` via `+1`), paired with `19`-insn `+2`-lane `rotate_pick` (`54–65` insns vs `Depravity`'s `76–139`), **zero `5–7`/`8–13` diagonal prey holds** (`threat:` splits immediately at `e >= 5` in `28` insns), **`0.0%` `t < 100` feed blackout**, and asymmetric post-`100` boxed feeding (`QUIET_FEED_CAP = 24` to keep `~98% e=50` interior scavenge density; `5x5`-enemy front cap `48` from `esi >= 49` for `+2/tick` stalemate drift).
3. **Ladder Discipline & Calibrated Outlook:**
   - **Keep `#2 Misfortune v3` (`cell 353`, `1826 / 247g`) untouched** as the ladder anchor; replace only **`cell 363` (`Depravity`)** after `Dogma` clears static checks, exhaustive Unicorn sweeps, and local `64x64` gauntlet gates.
   - **Calibrated Confidence of Overtaking `#1 CogSpore-Siect-F (1962)`:** **`40%–55%`**. `Dogma` closes `Misfortune`'s `t30–t100` opening deficit and `Cap B` / `e=50` drag, while tying `Siect-F` at `3` vs `3` repeats and `15` vs `15` `Gate-1`. Its single sharpest risk is losing `15 vs 3` on `t1` fresh contacts and `delay=0` newborns if `Siect-F`'s opening pace matches `first 8/2`.

---

## 2. Complete Lineage & Live Ladder State

### A. Chronological Cell Lineage (All 15+ Eras)

Instruction counts below measure **all executed instructions** (including taken jumps and `ret`) verified against `cells/gen_*.py`, `cells/depravity.asm`, and `data/site-checks.md`.

| Era / Cell (Generator / ID) | Architectural Delta from Parent | Exact Executed Insn Counts (Hot Bite / 1st Bite / Gate-1 / Walker or Split / Boxed) | Live Ladder Outcome (`ID`, Games, Wins, Peak & Final Rating) |
|---|---|---|---|
| **1. Sprint / Avarice** (`gen_sprint.py`, ID `149`) | Baseline stateless `F6` indirect jump (`jmp [fight_tbl+rax*8]`); 5x5 prey hold (`5..15` until `tick >= 2980`); never feeds. | Bite **6**; rest `<5`: **8**; hold (`5..15` w/ 5x5 enemy): **20**; split (no enemy / `>=16` / `>=2980`): **19 / 21 / 23**. | ID `149`: Peak **1355** (`223g`, **7th**); retired **1191 / 886g** (9th). Lost refill races vs AtomPush (`1/13`) & AtomCrasher (`3/10`). |
| **2. Covetous** (`gen_covetous.py`, ID `155`) | **Sprint** + **`F5` 5-insn bite** (`or al, [bite_tbl+rcx] / jnz EXIT_ADDR`) + **capped feeding** (`e >= 47` feeds poorest `<= 46`). | Bite **5**; rest `<5`: **9**; split (no enemy / `>=16` / late): **22 / 24 / 26**; boxed `<47` / feed `>=47`: **23–28 / <=60**. | ID `155`: Peak **1526** (`314g`, **3rd**), `+18pp` win rate (`60.4%` at `217g`); retired **1392 / 829g** (7th). |
| **3. Scourge** (`gen_scourge.py`, ID `156`) | **Covetous** + **11-insn Gate-1 stateless refill** (`REFILL_MIN=12`, `THREAT_MIN=16`, `act_tbl`/`thr_tbl`) + donor `FEED_D=16` (`margin=4`). | Bite **5**; Gate-1 (`>=12` / `>=16`): **11**; split `5..15` (clear / late): **24 / 25**; hold: **27**; rest `<5` / `<16`: **17**; feed `>=16`: **21–53**. | ID `156`: Reached **1st**, peak **1649** (`74/100` wins, `98%` refill); retired **1507 / 600g** (2nd). Trailed Atoms `t100–t200`. |
| **Shelved VEX: Woe / Conceit / Endemic** (`gen_woe/conceit/endemic.py`) | VEX 3-op (`vpcmpeqb`) variants of Scourge / Covetous / Contagion (`-1` on Gate-1 `11->10`, `-3` on Endemic boxed). | Woe/Conceit: Bite **5**, Gate-1 **10**; Endemic boxed max **79** (vs Contagion `82`). | **Never laddered.** `calib-s` (`104136`) & Woe Sandbox (`104123`, `104128`) proved site QEMU ignores VEX `vvvv`. |
| **4. Contagion** (`gen_contagion.py`, ID `157`) | **Scourge** + **tick-0 edge scout** (`EDGE=10, STEPS=10`) + **grab assist** (`e>=8`, no 5x5 enemy -> feed `<5` w/ empty edge) + `D=12`. | Bite **5**; Gate-1 **11**; split `5..15`: **26 / 25**; scout move: **40**; hold: **28**; rest `<5` / `<8`: **17**; boxed max **<=82**. | ID `157`: Peaked **1631 / 2117g (1603w)**, retired **1616 / 2145g, 1621w (75.6%)** (2nd, avg 78 insns/call). Lost `t75–200` to prey hold. |
| **5. Complacency** (`gen_complacency.py`, ID `174`) | **Scourge** -> **`FREE_UNTIL=3000` (deleted 5x5 prey-hold check)**. | Bite **5**; Gate-1 **11**; split `5..15`: **16**; rest `<5` / boxed `<16`: **17**; feed `>=16`: **21–53**. | ID `174`: Reached **1st** (`1576 / 282g`), peak **1608**, retired **1516 / 691g, 478w (69.2%)** (avg 46 insns/call). Packed dense early. |
| **6. Schism** (`gen_schism.py`, ID `176`) | **Complacency** + **outward boxed edge-feed** (`no 5x5 enemy, boxed, e>=6`: feed friend w/ empty neighbor). | Bite **5**; Gate-1 **11**; split `5..15`: **16**; rest `<5` / `<6`: **17**; grab feed: **32–48**; old feed max **63 / 86**. | ID `176`: **1st**, peaked **1675 / 1353g (1063w, 78.6%)** (`2026-11-09`); collapsed on `2026-11-10` AI field shift -> retired **1314 / 2814g**. |
| **7. Pestilence** (`gen_pestilence.py`, ID `180`) | **Schism** + **MOVE refill at `e >= 20`** ahead of `act_tbl`. | Bite **5**; move refill (`>=20`): **13**; Gate-1: **13** (Schism `+2` on every slow path; boxed max **88**). | ID `180`: **2nd** at **1576 / 377g (295w)**, avg 1.24; dropped to **1250 / 1649g** (`2026-11-11`). `+2` slow-path tax hurt. |
| **8. Bane v1** (`gen_bane.py`, ID `272`) | **Schism** -> **Restored 5x5 prey hold** (`5..15` w/ 5x5 enemy rests until `2980`) to halt contact slaughter. | Bite **5**; Gate-1 **11**; split `5..15`: **24 / 25**; hold: **27**; rest: **17**; grab feed: **32–48**; old max **63 / 86**. | ID `272`: **Regressed** to **10th (~1300, final 1307 / 44g)**. `0-2` CogBloomXT, `0-3` medivac; hold without dispersal starved growth. |
| **9a. Bane v2.0** (`c263b48`, ID `277`) | **Bane v1** + **`8/2` dispersal opening** (`K_LONG=8` forward, `K_SHORT=2` clockwise, `MOVE` walkers). | Bite **5**; Gate-1 **11**; walker move: **34**; settled split: **38–61**; rest/hold: **26 / 28**. | ID `277`: **+340 Elo jump** -> **1st**, retired **1645 / 157g (82% wins, avg 1.22)**. Still `0-3` medivac, `0-2` CogBloomXT. |
| **9b. Bane v2.1** (`gen_bane2.py`, ID `287`) | **Bane v2.0** + **4-insn checked stored bite** (`[2]` view offset, `[3]` action). | **Repeat bite 4**; **1st scan bite 16**; Gate-1 **16**; hold **33**; walker **39**; settled **43–66**; boxed max **91**. | ID `287`: **+160 jump** -> **1775 / 189g (93%, avg 1.07, 1st)** -> **1804 / 203g** before v2.2 swap. Eliminated medivac (`0-2%` bitten first). |
| **9c. Bane v2.2 ("Bane v4")** (`gen_bane2.py`, ID `289`) | **Bane v2.1** -> Narrowed prey hold from 5x5 to **3x3 diagonals only** (`kNearLo`/`kNearHi` at `6,8,16,18`). | **Repeat bite 4**; **1st bite 16**; Gate-1 **16**; diag rest/hold **31 / 33**; walker **39**; settled **43–66**; max **91**. | ID `289`: 298/329 single-cell (**91%**), beat VarSi `9/21`, Colossus `18/29`, **0/4 vs Siect-F**. Retired **1780 / 1933g** (#2). |
| *(Unshipped)* **Bane v2.3a** (`gen_bane3.py`) | **Bane v2.2** -> 16-bit `lock2_tbl` load/store (`16 -> 12` 1st bite). | **Repeat bite 4**; **1st bite 12**; slow paths identical to Bane v2.2 (**16 / 31 / 33 / 39 / 43–66 / max 91**). | **Not uploaded** (`+0..2.3%` race flip judged too small for rating reset). |
| **10. Conviction** (`gen_conviction.py`, ID `290`) | **Bane v2.2** -> **3-insn blind byte queue** (`shr qword [mem+8], 8 / or / jnz`), `Q_MIN=3..Q_MAX=7` (`0` if `te<=2`). | **Queued bite 3** (blind); **1st bite 19**; Gate-1 **14**; hold **31**; walker **37**; settled **41–64**; max **89**. | ID `290`: **1635 / 155g (3rd)**, `251/293` (`86%`). `83–90%` air-bites after kills, `13–22%` refill rate. Retired `2026-11-12`. |
| **11. Penalty** (`gen_penalty.py`, ID `302`) | **Conviction** -> Queue for `te <= KILL_MAX (8)` appends blind `[SPLIT]` into target square (`te<=2` queues `[SPLIT]`). | **Queued bite/split 3**; **1st bite 18**; slow paths same as Conviction (Gate-1 **14**, max **89**). | ID `302`: **Regressed** to `112/139` (`81%`), `10–17%` newborns killed within 5 ticks. Retired `2026-11-12`. |
| **12. Misfortune v1** (`gen_misfortune.py`, ID `350`) | **Bane v2.2** -> **2-insn `e`-slot blind bite** (`[esi+CELLMEM_BASE+13]`) + `xmm0` clear + `exact=1` (`k=0` at `te<=2`) + **Cap B** (`byte 63=0`, hold `>=48`, lift `>=47`). | **Armed bite 2**; **1st arm 19**; Gate-1 **15**; diag rest/hold **30 / 32**; walker **38**; settled **42–65**; Cap B hit **80** / miss `+56` (max **145**). | ID `350`: **#2 at 1697 / 137g**, retired **1751 / 172g**. Won `2/6` vs Siect-F (`1.6x–3x` area), `0/4` on equal/smaller area. |
| **13. Misfortune v2 ("AC1")** (`gen_misfortune2.py` `b40b1a4`, ID `352`) | **Misfortune v1** + **4 bundled changes**: checked refill (`byte 2`), `armed_children` (`e=1 mod 4`), `hold='off'`, `FEED_PAD=6` (`>=100`). | **Armed bite 2**; checked refill **13**; **1st arm 22/26/28**; Gate-1 **20–66**; max **151**. | ID `352`: **Catastrophic `-371` collapse** -> retired after **9 games, rating 1326** (`+115-120%` friendly fire, slow `arm:`/`Gate-1`). |
| **14. Misfortune v3 ("split10")** (`gen_misfortune2.py` `400bf88`, ID `353`, **LIVE**) | **Misfortune v1** (all AC1 changes reverted) + **`hold='split', hold_min=10`** (diag enemy w/ `e>=10` splits via `Gate-1`). | **Armed bite 2**; **1st arm 19**; Gate-1 **15**; `hold_split` (`>=10`): **29 / 31**; diag `<10`: **32 / 34**; walker **38**; settled **42–65**; Cap B **80** / max **144**. | ID `353`: **Current #2 — 1812 / 228g (82.9%, avg 1.17, 135 insns/call)** -> **1826 / 247g** (`data/site-checks.md:21,23`). |
| **15. Depravity** (`6cfb4a7`, ID `363`, **LIVE**) | **Misfortune v2 `arm_tbl`** -> deleted Cap B, added `T_FEED=200`, `arm_tbl` (`17`), `pat1_tbl` `k=0` stun-save, `HOLD_MIN=8`, settled `dir-open` (`76–139`). | **Armed bite 2**; **1st `arm_tbl` 17**; Gate-1 **15**; `hold_split` (`>=8`): **29 / 32**; `dir-open`: **76–139**; boxed `<200`: **23 / 33**; `>=200`: **38–86**; SB avg **57**, max **135**. | ID `363`: 1st in `16x16` Sandbox `151538` (pop `138 vs 33`), **stalled immediately in ladder game 1 vs AtomVirus & VarSi** (`48<->50` lock + `T_FEED=200` starvation). *(Local unshipped `e729e16` disregarded.)* |

### B. Live Top-10 Ladder Standings (`data/site-checks.md:21-24`)

| Rank | Cell | Rating | Games / Wins / Avg Place | Notes |
|---|---|---|---|---|
| **1** | **`CogSpore-Siect-F`** | **1962** | `2069g` / `1971w` (**95.3%**) / **1.05** | `87` median insns (`202` max); `<=3`-insn multi-dir combat (`=3` `84.6–91.3%`) |
| **2** | **`Misfortune v3` (`cell 353`, OURS)** | **1826** *(1812 @ 228g)* | `247g` (`189/228` = **82.9%**) / **1.17** | `23,674` B; **`135` insns/call**; shipped `2026-11-14 06:18 UTC` (`400bf88`) |
| **3** | **`CogSpore - VarSi v2`** | **1798** | `2256g` / **1.18** | `87` median insns (`203` max); `4`-insn `U/D` (`0% R/L <5`) |
| **4** | **`Colossus`** | **1752** | `2771g` / **1.28** | `65` median insns (`106` max); `5`-insn isotropic bite; high early feed |
| **5** | **`AtomVirus v10`** | **1671** | `1304g` / **1.31** | Fast `t100 = 2203` from `526` Voronoi area (`147068`); no decoded replays |
| **6** | **`medivac`** | **1517** | — | `47` median insns (`62` max); `5`-insn bite (`98.8%` bitten first by `Bane v2.2`) |
| **7** | **`CogBloomXT v4`** | **1488** | — | `51` median insns (`190` max); directional `4`-insn bite |
| **8** | **`NomNom2`** | **1318** | — | `5+`-insn bite (`99.7%` lost to `Bane v2.2` armed) |
| **9** | **`AtomPush v5`** | **1279** | — | Early Atom benchmark (`35` insns/call) |
| **10** | **`AtomCrasher v7`** | **1206** | — | Early Atom benchmark (`35` insns/call) |
| *(Active)* | **`Depravity` (`cell 363`, OURS)** | *(Unranked / new)* | Activated `09:35–09:40` | `18,602` B (`6cfb4a7`); stalled in game 1 vs `AtomVirus` & `VarSi` |

---

## 3. Empirical Replay Forensics & Rival Blueprints

> **Primary-Data Timeline Caveat:** All decoded `Siect-F` vs `Misfortune` replays in `data/siectf-growth-2026-11-13.md` and `data/siectf-games.md` (`146477`, `147456`, `147569`, `147688`, `148012`, `146773`) belong to **`Misfortune v1` (`cell 350`)**. Live `#2` **`Misfortune v3` (`cell 353`)**, shipped `2026-11-14 06:18 UTC`, adds `hold='split'` at `e >= 10` (`gen_misfortune2.py`) and has **no decoded replays in the repo**.

### A. Where 4-Colony Games Are Decided (`t30–t100` + Attrition)
1. **Start-Square Stratification vs Execution (`Bane v2.2`, `m-solo-matrix.txt`, `docs/evidence/bane-v22-evidence-2026-11-12.md:95-117`):**
   - On `313` single-own-cell games (`288W/25L = 92.0%`), `VarSi` accounted for `10` losses, `Colossus` `8`, `CogSpore` `5`, `CogBloomXT` `2`, plus `0/4` vs `Siect-F`.
   - `bad` starts (`d < -250` solo `t60` delta) match solo board geometry (`-49%` at `t60` on corners/walls). `Colossus` losses share the exact same window-`b` split gap as wins (start-driven).
   - **`equal` starts (`-250..+250`):** `Bane v2.2` went **`0/5` vs `VarSi`**, falling `100–320` cells below solo expectation by `t60` and `100–1200` by `t100`.
   - **`good` starts (`d > +250`):** `Bane v2.2` went `8W/2L` — both losses to `Siect-F` (`131245` `+672` at `t100`, `131332` `+1063` at `t100`).
   - Across `17` decoded `Bane v2.2` losses, **`14/17` (`82.4%`) were decided between `t30` and `t100`** (`ahead` in `13/17` at `t30` -> `3/17` at `t60` -> `2/17` at `t100`). Pooled `38`-game Spearman correlations with final share (`eval-all.txt:1261-1305`): `p200 +0.93`, `p100 +0.92`, `g100 +0.91`, `p60 +0.89`, `t0_split +0.86`, `t30_hold -0.70`.
2. **Root Causes Inside `t30–t100`:**
   - **Prey-hold split starvation:** In equal-start `VarSi` losses (`m2-varsi-budget.txt`), `Bane`'s `near+front` (`open, e>=5`) split rate collapsed to **`37.8% / 28.7% / 30.5%`** vs `VarSi` **`83.0% / 58.1% / 42.8%`** (`a/b/c`); `85%` (`938/1094` in `b`) of near idle was the diagonal prey hold. In `m1-gate-summary.txt`, holds caused **`35.6% / 27.3% / 26.4%`** (`a/b/c`) of lost contested square-ticks (`5–7` holds lost the square `78% / 60% / 61%`).
   - **Premature early feeding & own-cell collisions:** `Bane`/`Misfortune` spent `1.8% / 5.9% / 14.0%` (`far` `a/b/c`) on feeding while `VarSi` and `Siect-F` kept **`0.0%` feed across `a–c`**. Meanwhile `Bane`'s static clockwise splits collided with own cells (`7.9 / 18.6 / 23.3%` far `none`, identical to solo `7.6 / 18.4 / 22.3%`).
3. **Why `Misfortune v1` (`2`-Insn Bite) Still Lost `787 vs 3309` to `Siect-F` (`3`-Insn Bite) in `146477`:**
   - `Misfortune v1` **won `89%` of `172,800` `bitten_first` engagements at `t300+`** (`t100–300`: `81% vs 13%`), yet still lost `787 vs 3309` (`siectf-games.md:2`, `siectf-growth-2026-11-13.md:40-53`)! Across all `6` shared matches, `Misfortune v1` won only on `1.6x` (`147456`) and `3.0x` (`147688`) Voronoi start area, and lost all `4` with equal (`147569`: led `161 vs 116` at `t30`, then `Siect-F` grew `1.35x` faster to `960 vs 711` at `t60` and `1.6x` to `1835 vs 1125` at `t100`) or smaller area (`146477`: led `152 vs 131` at `t30`, crushed `513 vs 1125` at `t60` and `744 vs 2266` at `t100`).
   - **Resolving the `3`-Insn vs `2`-Insn Paradox:** `2`-insn combat did not fail; **`Misfortune` lost on non-repeat macro execution**: `t < 100` feeding, `5–9` diagonal holds (`v3` still holds `5–9` until `2980`), `42–65`-insn clockwise splits, `19`-insn `arm:` (`exact=1` `k=0` rescan penalty at `te<=2`), `Cap B` energy burn (`1.7e/pull`, `135` insns/call vs `Siect-F`'s `87`), and unbacked `e=50` cliffs.

### B. Rival Blueprints (`#1`, `#3`, `#4`, `#5`)

| Dimension | `#1 CogSpore-Siect-F` (`1962`, `1.05`) | `#3 CogSpore-VarSi v2` (`1798`, `1.18`) | `#4 Colossus` (`1752`, `1.28`) | `#5 AtomVirus v10` (`1671`, `1.31`) |
|---|---|---|---|---|
| **Sample / Insns** | 5g decoded (`87`, max `202`) | 17g decoded (`87`, max `203`) | 24g decoded (`65`, max `106`) | **No decoded replays in repo** |
| **Bite Tiers (`m10` / `order-exact`)** | `m10`: **`=3` `84.6% / 91.3%`**, `<3` `5.6%/4.4%`, `=4` **`0.0%`**. `first a/b <4`: **`64.5 / 75.8%`**, `repeat 5-15`: **`0.0 / 0.0%`**, `other`: `0.6 / 32.7%` | `first a/b =4`: **`50.6 / 82.4%`**, `repeat a/b =4`: **`71.7 / 83.4%`**, `<4`: `3.1–5.4%` | `v2.0` vs 5-markers: **`91–95% =5`**; `v2.2`: `first 5-15` `57.3 / 75.7%`, `other` `26.6 / 64.9%` | N/A |
| **Directional Profile (`order-dir`)** | `<4` all 4 dirs (`U 17.9 / R 16.3 / D 28.3 / L 37.5`; per-game `D 92%`, `L 99%`, `U 91%`); `5-15` `88% U/R` | `<4` & `=4`: **`100% U/D` (`U ~57-60%, D ~40-43%, R/L 0.0%`)**; `5-15` mostly `L/R` | `5-15` biased `R 43.4 / U 25.0 / L 23.9 / D 7.7` | N/A |
| **Empty-Test (`blind-summary2`)** | `self`: eat `84.8` / none `14.8`; `other`: eat `89.1` / none `10.4`; `refill-test`: `99.2%`. `m5 t0=none nb=1`: skipped `E2` & bit refill `t1` (`72.0%` eat-c) | `self` eat `84.1` / none `15.4`; `other` `91.0` / `8.2`; `refill-test` `95.1%` | `self` eat `95.2` / none `4.6`; `other` `98.7` / `1.1` | N/A |
| **Refills & Duels vs `Bane v2.2`** | **`~15`-insn `t+1` refill** (`76.8%` 1st-tick, steals `89.6%` at `t0`; `226 vs 154` `freed_S_cell` in `146477`). Duels: `Bane` armed `82.4/10.7`, **`S` armed `0.0 / 99.8%`**, stun `8.5–14.5%` | `78.5%` 1st-tick, `79.4%` dead5. Duels: `Bane` armed `81.6/15.4`, `V` armed `32.8/58.6`, stun `40–66%` | `94.0%` 1st-tick, `72.4%` dead5. Duels vs v2.2: `Bane` armed `99.9/0.0`, `C` armed `11.5/83.5` | N/A |
| **Macro Budgets (`a..e`)** | `a`: split `15.7`, **move `28.9`**, **feed `0.0`**; `b–c`: **feed `0.0`**; `e`: **feed `0.7%`**, **`e 50: 98.2%`** | `a`: split `15.0`, **move `27.7`**, **feed `0.0`**; `b–c`: **feed `0.0`**; `e`: feed `10.5%`, `e 50: 83.6%` | `a`: split `14.6`, move `12.6`, **feed `16.4`**; `b/c`: feed **`50.6 / 56.1`**; `e 50: 72.5%` | **`t100 = 2203`** from `526` area (`147068`, `siectf-growth:21`) |

### C. Resolving `Siect-F`'s Mechanism (`<= 3`-Insn Multi-Directional Combat)
- **What is ruled out:**
  - *4-insn pointer-checked stored bite (`movzx/cmp/mov/je`):* Impossible in `3` insns because `VIEW_CELLS` ortho offsets `(7,11,13,17)` are non-contiguous; falsified by `=4 = 0.0%` in `m10-siect-cost.txt` and `99.8%` loss by `Bane v2.2` (`duel-summary.txt:27`).
  - *Single fixed-direction 3-insn check alone:* Falsified by `<4` operating in all 4 directions (`D 28.3%, L 37.5%, U 17.9%, R 16.3%`).
  - *`2`-insn primary `e`-slot:* Falsified by `=3 = 84.6–91.3%` in `m10` and `11% vs 89%` (`bitten_first`) loss to `Misfortune v1` in `146477`.
  - *`Conviction`-style `Q_MIN >= 1` blind queue:* Falsified by `self/other none = 14.8% / 10.4%` vs `Conviction`'s `83.3% / 89.8%`.
- **What is consistent:** A **`3`-insn blind queue/counter with `Q_MIN=0` + queue inheritance on split** (possibly combined with 1 fixed-direction `3`-insn check + `U/R`-slow scan), matching `=3` (`84.6–91.3%`), all-4-dir `<4`, `repeat 5-15 = 0.0%` (`26`-tick chains in `131245`), `first <4 = 64.5 / 75.8%`, and `m5 t0=none nb=1 -> t1 eat-c 72.0%` (proving a blind bite on `S` while `E2` was adjacent).

---

## 4. ABI v4, Ruleset v9, & `ALLOWED` x86-64 Combat/Picker Boundaries

### A. Verified Environment & Ruleset Constants (`docs/cellhack.inc`, `sim/engine.py`)
- **ABI / Memory Map (`ABI_VERSION = 4`):** `CODE_BASE = 0x100000`, `CODE_MAX = 0x8000` (`32,768` B ceiling), `VIEW_BASE = 0x300000` (`rdi`), `CELLMEM_BASE = 0x310000` (`rdx`), `MEM_SIZE = 64` (inherited parent -> child on `ACT_SPLIT` **after** parent's Decide writes, `engine.py:663`), `CELLMEM_SIZE = 4096` (bytes `64..74` are writable scratch on `movdqu`, though unpersisted), `EXIT_ADDR = 0x400000`, `INSN_BUDGET = 1000`.
- **Entry & Counting (`calib-c/e/q/r`, `issues.md:66`):** `rdi = VIEW_BASE`, `rsi = energy` (`1..50`, zero-extended), `rdx = CELLMEM_BASE`, `rax = rbx = rcx = rbp = r8..r15 = 0`, `xmm0..xmm15 = 0`, `[rsp] = EXIT_ADDR`. **Every executed instruction counts** (including `ret` and taken jumps like `jnz EXIT_ADDR`).
- **Ruleset v9 (`RULESET_VERSION = 9`):** `ENERGY_START = 10`, `ENERGY_MAX = 50` (clamped at Tidy; `cap_mid_tick=False`), `REST_GAIN = 1`, `SPLIT_MIN = 5` (`child = floor(e/2)`, `parent = ceil(e/2)`), `EAT_TAKE = 2` (failed `ACT_EAT` gains `0`, `t_failed_eat.asm`, `engine.py:596`), `FEED_AMOUNT = 2`, `stun_keeps_memory = True` (verified live by `m9-stun-memory.txt:4`: `Bane v2.2` `stunprev` lands `81.5%` at `=4`).
- **Key `VIEW_BASE` Offsets:** `VIEW_TICK = 0` (`u32`), `VIEW_RAND = 6` (`u8`), `VIEW_AGE = 7` (`u8`, `0` on birth tick 1), `VIEW_X = 8` (`u16`), `VIEW_Y = 10` (`u16`), `VIEW_CELLS = 32` (`u8[25]`: `0=empty, 1=friend, 2=enemy, 3=wall`; ortho `{7,13,17,11}` = `UP,RIGHT,DOWN,LEFT`), `VIEW_ENERGIES = 64` (`u8[25]`, `0` for empty/wall).

### B. `ALLOWED` ISA & Structural Boundaries (`cells/check_cells.py:66-71`)
- **Legal Instructions:** `db, dw, dd, dq, times, align`; scalar `mov, movzx, lea, or, and, xor, sub, add, inc, dec, shl, shr, cmp, test, ja, jae, jb, jbe, je, jne, jz, jnz, jmp, ret, cmova, cmovae, rep, stosb`; SIMD `movdqu, movdqa, pcmpeqb, pmovmskb, por, pxor, pand, vpcmpeqb, vpmovmskb, vpxor`.
- **Forbidden (Site Faults):** `xchg`, `cmove/cmovz/cmovnz`, `bt`, `bsf/bsr`, `popcnt`, `pshufb`, `ptest`, signed `jcc`, `ymm*`.
- **QEMU Traps:** VEX `vpcmpeqb` must satisfy `dst == src1` (`calib-s` / `vex_dst_not_src1`); all `LEGACY_SSE` memory operands (`movdqa/pcmpeqb/por/pxor/pand`) must be `align 16`; all `esi`-indexed operands use `0x67` prefix; `movdqu` is unaligned-safe.
- **Exhaustive `<= 3`-Insn Combat Classification:**
  1. **`C1` (`2`-insn `e`-slot `or al, [esi+CELLMEM_BASE+13] / jnz`):** Cannot clear `slot[50]` in 2 insns (`no xchg`); `slot[50]==0` creates the `48 <-> 50` cliff; `2+`-enemy `+2-2=0` energy stasis drives unbounded friendly fire.
  2. **`C2` (`3`-insn `sub byte [rdx+2], 1 / mov al, [rdx+3] / jae`):** Legal (`dec` wraps `0->255` and fails!), zero `e=50` cliff, up to `254` ticks, **but requires `+2` cleanup** -> `16`-insn `Gate-1` (`1` behind `Siect-F`).
  3. **`C3a` (`3`-insn byte shift `shr qword [rdx+8], 8 / or al, [rdx+8] / jnz`):** `0` cleanup (`14`-insn `Gate-1`, `13`-insn `arm:`), **but capped at `7` ticks (`14` dmg)** -> 8th-tick `-2e` stun leak vs `50e` enemies.
  4. **`C3b` (`3`-insn bitmask shift `shr qword [rdx+8], 1 / mov al, [rdx+16] / jnz`):** `0` is fixed point of `shr` (auto-zeroes `[rdx+8]`, **`+1` cleanup `xor eax, eax`**), **`15`-insn `Gate-1`**, **`15`-insn `arm:`**, up to **`63` consecutive bites**, zero `e=50` cliff, arbitrary calibrated `k(te)`.
  5. **`C4` (`3`-insn fixed-dir `cmp/mov/je`):** Only checks `1` of `4` ortho directions (`VIEW_CELLS` strides `39,43,45,49` forbid multi-dir check in `<= 3` insns).
- **`9`-Insn `+2`-Lane Picker Primitive (`1,540` B total):** `movdqu xmm1, [rdi + VIEW_CELLS + 2]` captures `idx 2..17` (`UP2=0, UP=5, L2=8, L=9, R=11, R2=12, DOWN=15`); `pcmpeqb` with `[kOpen7]` + `pmovmskb r8d, xmm1` + `open_lo[r8b]` (`256` B) + `open_hi[r8d>>8]` (`256` B) + `d2_tbl[[rdi+VIEW_CELLS+22]]` (`4` B) builds `r9b = (plus2_empty4 << 4) | ortho_empty4`, combined with rotation `(bearing+1)&3 << 8` into `dir_pick_tbl` (`1,024` B).

---

## 5. Clean-Sheet Architecture Evaluation & Red-Team Kill-Log

Three clean-sheet families were designed and subjected to independent ISA/ABI audit (Stage 5) and empirical red-team stress testing (Stage 6).

| Candidate / Mechanism | Stage 5 Audit | Stage 6 Red-Team Verdict & Exact Evidence |
|---|---|---|
| **Family 2: `Sub-3 Ambush` (`C1` `2`-insn `e`-slot + `low_e`/`boxed:` pre-arms + unpadded `Cap B`)** | **`REJECT`** | **Killed on both implementation bugs and structural limits:** (1) `low_e` speculative `slot[e+1]` pre-arm causes an infinite `2`-insn air-bite brick via `t_failed_eat` (`0` energy gain, skipping `e0` wipe) + `0x1515` wrong-dir bites; (2) `boxed:` odd-`e` newborn pre-arm fails via prefix wipe before `Gate-1` and `REST +1`/`FEED -2` parity shift; (3) **Fundamental `C1` failure:** `52.3%` `2+`-enemy contacts (`m11-contact-stats.txt`) trigger `4.5/100` friendly bites (`82%` at `e<=47`), `92.3%(a)/38.1%(b)` unbacked kills lock `48<->50`, and `Cap B` burns `1.7e/pull` (`90,384e / 52,620` pulls, `issues.md:8`). |
| **Family 1's `age==0` `1`-step `ACT_MOVE` + `(X+2Y)&3`** | Pass w/ `r8d` fix | **KILLED (`FATAL OPENING COLLAPSE`):** `opening-search-2026-11-11.md:14,24-25` shows `no long walks, 1 step` scored `t20=65, t40=310, t60=670, t100=1734` vs `Bane v2.2` `2942` and `first 8/2` `3012` — **`-42.4%` collapse at `t100`** (`age==0` `e=2..4` moves even less, losing map before `t100` vs `AtomVirus 2203` & `Siect-F 1835–2266`). |
| **Family 1's Unbounded `k(te) = min(63, te+6)` & `k(1..2)=0`** | Pass | **KILLED (`FATAL BLIND OVER-ARMING` + `te<=2` BUG):** `52.3%` multi-enemy ticks + `64–78%` kills within `12` ticks (`H=4.9–7.2`) mean `te=30..50` fires `36–56` blind air-bites/friendly-refill kills on crossfire/KS. Meanwhile `k(1..2)=0` fails to exploit `stun_keeps_memory=True` (`81.5%`, `m9-stun-memory.txt:4`), re-paying `15` insns on `t2` after a `15 vs 3` stun. |
| **Family 3: `Land-Rush` (`C3a` `shr .., 8` + `sparse-stop 2`)** | Pass w/ 3 bug fixes (`edx` crash, `byte` size, `r9d` clobber) | **KILLED:** (1) `C3a` leaks `-2e` every 8th tick (`-0.25 e/tick` at `13`-insn `arm:`) in unsupported `50e` `1v1` duels (`38.1%` of `b` kills lack boxed friends); (2) **`sparse-stop 2` is empirically broken** in `opening-search-2026-11-11.md:20` (`t60=964 -9.3%`, **`t100=2460 -16.4%`** vs `v2.2`), and `open-long 16/2 sparse-stop 4` regressed on `6/11` starts (`-30.2% / -29.8%` at `t20`, `m-solo-matrix.txt:58-64`). |
| **`REFILL_MIN = 14` in `Gate-1`** | Contradiction | **KILLED:** Skipping `e=12..13` on `Gate-1` drops cells into `split_open` anyway (`39–65` insns instead of `15`, spawning the same `6e` child late while `Siect-F` steals `89.6%` at `t0`, `m8b`). **`REFILL_MIN = 12`** dominates. |
| **Converged Survivor: `Dogma` (`C3b` Calibrated + `first 8/2`)** | **Audited Exact** | **SURVIVES ALL GATES:** Combines `C3b` (`3 / 15 / 15`, `K_CAP=16`, `k(1..2)=1`) and asymmetric `boxed:` (`24` quiet / `48` front, `t<100` zero feed) with proven **`first 8/2`** (`0/11` solo regressions, `t100=3012`), zero diagonal holds, and `+2`-lane `rotate_pick`. |

---

## 6. Final Converged Clean-Sheet Specification: `Dogma`

### A. `MEM[0..63]` Layout & Core Parameters
- **`MEM[0]` (`byte`):** `bearing` (`0..3`, initialized `0` on spawn).
- **`MEM[1]` (`byte`):** `steps_left` (`0..8`).
- **`MEM[2..3]`:** `0` (unused).
- **`MEM[4..7]` (`dword`):** `(VIEW_X | (VIEW_Y << 16)) + 1` (`last_split_pos`: `+1` ensures `(0,0)` encodes as `1 != 0`, eliminating `Bane2`/`Depravity`'s `(0,0)` false match).
- **`MEM[8..15]` (`qword`):** `C3b` bitmask `1ULL << k` (`0` = unarmed; `shr qword [rdx+8], 1` shifts 1 bit right/tick -> `k` blind bites before hitting `0` with `ZF=1`).
- **`MEM[16]` (`byte`):** Armed eat action `ACT_EAT + d` (`0x30..0x33`).
- **`MEM[17..63]`:** `0` (unused).
- **Constants & Ablation Knobs:**
  - `REFILL_MIN = 12`, `THREAT_MIN = 16` (`thr_tbl`; boxed `255`).
  - `kmask_tbl` (`256 × dq` = `2,048` B): `te=0 -> 0`; **`te=1..2 -> k=1` (`2`)**; **`te >= 3 -> k = min(16, (te // 2) + 2)`** (`K_CAP = 16`; local ablation knobs: `K_CAP = 12` vs `16` vs `25`, `k(1..2) = 1` vs `0`).
  - `T_FEED_MIN = 100` (`0.0%` `a–c` feed); **`QUIET_FEED_CAP = 24`** (`cmp esi, 28 / cmovae`; local ablation knob: `24` vs `28` vs `38`); **`FRONT_FEED_CAP = 48`** (`cmp esi, 49 / cmovae`).

### B. Exact NASM Control Flow & Verified Instruction Counts

All `LEGACY_SSE` constants (`kEnemy, kRefill, kNearLo, kNearHi, kOpen7, kTwoLo, kTwoHi`) are `align 16`. Every `pmovmskb` outside `Gate-1`/`kEnemy` uses **`r8d`**, never `edx`, preserving `rdx = CELLMEM_BASE`. Upon falling through `jnz EXIT_ADDR`, **`[rdx+8]` is guaranteed `0`** across `Gate-1`, `boxed`, `threat`, `walker`, and `settled`.

1. **Hot Armed Bite (`start:`, `3` insns):**
   - `1`: `shr qword [rdx+8], 1` (`ZF=1` iff result `== 0`)
   - `2`: `mov al, [rdx+16]` (`mov` preserves `ZF`)
   - `3`: `jnz EXIT_ADDR` -> **`3` insns**.
2. **Miss + `kEnemy` Scan + `arm:` (`15` insns):**
   - `4`: `xor eax, eax` (wipes stale `[rdx+16]` from `al`)
   - `5–9`: `movdqu xmm0, [rdi+VIEW_CELLS+VIEW_UP]` / `pcmpeqb xmm0, [kEnemy]` / `pmovmskb ecx, xmm0` / `or al, [abs bite_tbl+rcx]` / `jnz arm`
   - `10`: `jmp [abs arm_tbl - ACT_EAT*8 + rax*8]` (`FF 24 C5 disp32`, `arm_tbl >= CODE_BASE > ACT_EAT*8`)
   - `11–15` (`arm_d`): `mov [rdx+16], al` / `movzx ecx, byte [rdi+VIEW_ENERGIES+IDX_d]` / `mov r8, [abs kmask_tbl+rcx*8]` / `mov [rdx+8], r8` / `ret` -> **`15` insns**.
3. **`Gate-1` Refill / High-E Split (`slow:`, `15` insns):**
   - `1–9` (fall through `jnz arm`, `[rdx+8] == 0`)
   - `10–15`: `movdqu xmm1, [rdi+VIEW_CELLS+6]` / `pcmpeqb xmm1, [kRefill]` / `pmovmskb ecx, xmm1` / `mov al, [abs act_tbl+rcx]` / `cmp sil, [abs thr_tbl+rcx]` (`REFILL_MIN=12`, `THREAT_MIN=16`, boxed `255`) / `jae EXIT_ADDR` -> **`15` insns**.
4. **Boxed Branch (`17` insns to `boxed:`):**
   - `16–17`: `test al, al` / `jz boxed`.
5. **Diagonal Enemy Stop (`kNearLo`/`kNearHi` BEFORE `first 8/2`, `25` insns so far):**
   - `18–25`: `movdqu xmm1, [rdi+VIEW_CELLS]` / `movdqu xmm2, [rdi+VIEW_CELLS+9]` / `pcmpeqb xmm1, [kNearLo]` / `pcmpeqb xmm2, [kNearHi]` / `por xmm1, xmm2` / `pmovmskb r8d, xmm1` / `test r8d, r8d` / `jnz threat` (`25` insns).
   - **`threat:` (`28` split / `30` rest):** `26` `mov byte [rdx+1], 0` / `27` `cmp esi, 5` / `28` `jae EXIT_ADDR` (**`28` insns** immediate split via `Gate-1`'s `al`, zero `5–7`/`8–13` diagonal holds!) / `29` `mov al, ACT_REST` / `30` `ret` (**`30` insns** rest for `e=1..4`).
6. **Proven `first 8/2` Walker (`MEM[0..7]`, runs BEFORE `cmp esi, 5` so `5e` first children walk `8` steps):**
   - `26–31`: `mov ecx, [rdi+VIEW_X]` / `inc ecx` (`+1` fixes `(0,0)`) / `cmp byte [rdx+1], 0` / `je settled` (`29`) / `cmp ecx, [rdx+4]` / `je settled` (`31`).
   - `32–39`: `movzx r9d, byte [rdx+0]` / `and r9d, 3` / `movzx r10d, byte [abs dir_idx+r9]` / `cmp byte [rdi+VIEW_CELLS+r10], CELL_EMPTY` / `jne walk_end` (`36`) / `dec byte [rdx+1]` (`byte` size!) / `lea eax, [r9+ACT_MOVE]` / `ret` -> **`39` insns**.
   - `walk_end:` `mov byte [rdx+1], 0` (`37` at `settled:`).
7. **`settled:` (`33 / 35 / 41` rest; `43` `first 8`; `54 / 56 / 57 / 65` `rotate_pick`):**
   - Entered at `29` (`steps==0`), `31` (`steps>0, pos==last_pos`), or `37` (`walk_end`):
   - `+1..2`: `cmp esi, 5` / `jb rest` -> `rest:` (`mov al, ACT_REST` / `ret`) = **`33 / 35 / 41` insns** (matching `gen_bane2.py:86-87` identically).
   - `+3..9` (`e >= 5`): `movzx r9d, byte [rdx+0]` / `and r9d, 3` / `cmp ecx, [rdx+4]` / `je rotate_pick` (`35 / 37 / 43`) / `movzx r10d, byte [abs dir_idx+r9]` / `cmp byte [rdi+VIEW_CELLS+r10], CELL_EMPTY` / `jne rotate_pick` (`38 / 40 / 46`).
   - **First child forward (`K_LONG = 8`, `43` insns):** `39–43` `mov byte [rdx+1], 8` / `mov [rdx+0], r9b` / `mov [rdx+4], ecx` / `lea eax, [r9+ACT_SPLIT]` / `ret` (**`43` insns**).
   - **`rotate_pick:` (`K_SHORT = 2`, `19`-insn body -> `54 / 56 / 57 / 65` insns):**
     1. Rotation (`3` insns, computed BEFORE `+2`-lane primitive so `r9d` is not clobbered): `lea r10d, [r9+1]` / `and r10d, 3` / `shl r10d, 8`.
     2. `+2`-lane primitive (`9` insns): `movdqu xmm1, [rdi+VIEW_CELLS+2]` / `pcmpeqb xmm1, [kOpen7]` / `pmovmskb r8d, xmm1` / `movzx r9d, r8b` / `movzx r9d, byte [abs open_lo+r9]` / `shr r8d, 8` / `or r9b, [abs open_hi+r8]` / `movzx r8d, byte [rdi+VIEW_CELLS+22]` / `or r9b, [abs d2_tbl+r8]`.
     3. Emit (`7` insns): `or r9d, r10d` / `movzx r11d, byte [abs dir_pick_tbl+r9]` (`0..3`, selecting first dir in clockwise order from `(bearing+1)&3` with both ortho and `+2` empty, else first ortho-empty; `open_lo[256]`, `open_hi[256]`, `d2_tbl[4]` use ortho bits `0..3` and `+2` bits `4..7` for `U,R,D,L = 0..3`) / `mov byte [rdx+1], 2` / `mov [rdx+0], r11b` / `mov [rdx+4], ecx` / `lea eax, [r11+ACT_SPLIT]` / `ret`.
     *(Note: an earlier Stage 7 draft approximated these as `32/34/40` rest, `43/45` first-8, and `56/57/62/65` rotate-pick; the instruction-by-instruction audit above gives the exact NASM counts `33/35/41`, `43`, and `54/56/57/65`.)*
8. **`boxed:` (`21 / 23 / 47–68` insns):**
   - `18–19`: `cmp dword [rdi+VIEW_TICK], 100` / `jb rest` -> **`21` insns** (`0.0%` `t < 100` feed).
   - `20–21`: `cmp esi, 16` / `jb rest` -> **`23` insns**.
   - `22–29`: `5x5` enemy check (`movdqu` `+0`/`+9`, `pcmpeqb [kTwoLo/Hi]`, `por`, `pmovmskb r8d, xmm1`, `test r8d, r8d`, `jnz boxed_front`).
   - Threshold (`4` insns fallthrough / `5` insns jump = `33` / `34` before `find_poorest`):
     - **Quiet interior (`r8d == 0`, `QUIET_FEED_CAP = 24`):** `lea r9d, [rsi-4]` / `mov r10d, 24` / `cmp esi, 28` / `cmovae r9d, r10d` -> `jmp find_poorest` (`34`). Stops interior churn above `24e` (`e >= 28` feeds only `<= 24`), holding `~98% e=50` density for `25e` 3rd-colony scavenge refills.
     - **`5x5` enemy front (`r8d != 0`):** `lea r9d, [rsi-4]` / `mov r10d, 48` / **`cmp esi, 49`** / `cmovae r9d, r10d` (`33`). At `e=16..48`, feeds friends `<= e-4`; at `e=49..50`, feeds `<= 48` front cells (`+2/tick` sustain with `0` `cap=50` feed burn).
   - **`find_poorest:` (`depravity.asm:312-348`, `14..34` insns -> `47–68` total; `53–68` practical w/ `>= 2` friends):** `2` setup (`mov r8d, 255 / mov eax, ACT_REST`) + `4` dirs (`2` non-friend, `5` not-poorer, `7` new-poorest) + `3` (`ret` on feed) / `4` (`ja rest` -> `mov al, ACT_REST / ret`).

### C. Binary Footprint
`bite_tbl` (`1,106` B) + `act_tbl` (`7,608` B) + `thr_tbl` (`7,608` B) + `arm_tbl` (`32` B) + `kmask_tbl` (`2,048` B) + `+2`-lane picker (`256 + 256 + 4 + 1,024 = 1,540` B) + `dir_idx` (`4` B) + `7` aligned SSE constants (`112` B) + code (`~564` B) = **`~20,622` B (`~20.1 KiB` / `~20.6 KB` `<= 32,768` B `CODE_MAX`)**.

---

## 7. Falsifiable Pre-Ladder Build, Unicorn & Arena Verification Plan

1. **Static & ABI Audit (`cells/check_cells.py`):**
   - Zero mnemonics outside `ALLOWED`, zero `ymm` or VEX `dst != src1`, all `LEGACY_SSE` memory operands `align 16`, zero `org/bits/section/%include` directives, `jnz EXIT_ADDR`/`jae EXIT_ADDR` encodings verified, binary `~20,622` B (`~20.1 KiB <= 32,768` B).
2. **Unicorn Exhaustive Unit & Differential Sweep:**
   - Assert clean `MEM[0..63]` invariants across all paths (`MEM[8..15] == 0` on `Gate-1`/`threat`/`walker`/`settled`/`boxed`; `MEM[0..7]` updates `(bearing, steps_left, last_pos+1)`; `MEM[17..63] == 0`).
   - Exhaustively test: `k = 0..63` bitmask shift countdowns; `e = 1..50` (explicitly verifying `e = 48, 49, 50` zero cliff & `boxed_front` `cmp esi, 49` boundaries); `(0,0)` start coordinates (`+1 != 0`); `te = 0..50` (`kmask_tbl` with `k(1..2)=1` and `K_CAP=16`); `stun_keeps_memory=True` (`t1` `arm:` -> `t2` `3`-insn bite, noting `Decide` runs before stun so stunned blind ticks consume 1 bit); and zero `rdx` clobber on every path.
   - Verify exact Unicorn instruction counts match Section 6 (`3` / `15` / `15` / `21` / `23` / `28` / `30` / `33,35,41` / `39` / `43` / `54,56,57,65` / `47–68`).
3. **Local Arena Gauntlet & Pass/Fail Gates (BEFORE Any Ladder Upload):**
   - **Opponents & Maps:** `Misfortune v3 (353)` (`400bf88`), `Bane v2.2 (289)`, `Depravity (6cfb4a7)`, plus local `Siect-F` (`3`-insn counter + `15`-insn `Gate-1` + `0%` `t<100` feed + `98% e=50`), `VarSi` (`4`-insn U/D), and `AtomVirus` archetypes across `16x16` (`500t`), `64x64` 4-player (`3000t`, `m-solo-matrix.txt` starts, paired mirrored slots per `issues.md:27`), and `1v1` `50e` sustained duels (`3000t`).
   - **Ablations:** Sweep `K_CAP = 12 / 16 / 25`, `k(1..2) = 1 / 0`, and `QUIET_FEED_CAP = 24 / 28 / 38`.
   - **Hard Pass/Fail Gates:**
     1. `0` faults, `0` `48 <-> 50` locks, `t < 100` feed `== 0.0%`, and `0/11` `t20–t100` solo regressions vs `Bane v2.2` (`m-solo-matrix.txt`).
     2. Clear win-rate & avg-place dominance over `Misfortune v3 (353)`, `Bane v2.2 (289)`, and `Depravity (6cfb4a7)` on `64x64` multi-seed 4-player matches.
     3. Net positive H2H vs local `Siect-F` proxy on equal-start `64x64` 4-player and backed `1v1` front duels.
4. **Dual-Slot Ladder Discipline:**
   - **Preserve `cell 353` (`Misfortune v3`, `1826 / 247g`) untouched.**
   - **Replace only `cell 363` (`Depravity`, `6cfb4a7`)** after all local gates pass (using scripted POST + source verification guard per `issues.md:35`).

---

## 8. Calibrated Confidence (`40%–55%`), Residual Risks & Failure Conditions

- **Calibrated Probability of Cleanly Overtaking `#1 CogSpore-Siect-F (1962)` on Live Ladder:** **`40%–55%`**.
  - **Ground truth backing this estimate:** `Misfortune v1 (350)` won `89%` `bitten_first` at `t300+` in `146477` yet lost `787 vs 3309` because of `t30–t100` expansion deficit and `freed_S_cell` (`154 vs 226`); live `Misfortune v3 (353)` (`1826`, no decoded replays) still pays `5–9` holds, `t<100` feeds, `42–65`-insn clockwise splits, and `Cap B` burn (`135` insns/call). `Dogma` pairs `first 8/2` (`t100=3012`, `0/11` regressions) with `0%` `t<100` feed, `0` diagonal holds, and `C3b` (`3/15/15`, zero `e=50` cliff).
  - **Inference:** Closing the `t30–t100` macro gap while trading `Siect-F` even (`3 vs 3` / `15 vs 15`) and winning `b–e` attrition via `+2` front drift (`e<=48`) and quiet `e=50` density (`QUIET_FEED_CAP=24`) yields a credible path past `1962`, **but is not guaranteed** without a speed advantage on repeat or `t1` bites.
- **Primary Failure Conditions (What Would Cap `Dogma` at `~1900–1950`, `#2`):**
  1. **`15 vs 3` `t1` Vulnerability & `3 vs 3` Repeat Parity:** `Dogma` enters fresh contacts and `delay=0` refills unarmed (`15 vs 3`) and only coin-flips (`50/50`) armed repeats against `Siect-F`'s pre-queued `3`-insn tempo (`64.5–75.8%` `first <4`, `89.6%` `t0` steal). If `Siect-F`'s early macro pace equals `first 8/2` on live maps and `delay=0` `freed_S_cell` bleeding outweighs `+2` front sustain, `Dogma` may stall just shy of `1962`.
  2. **`K_CAP` Mismatch in Multi-Enemy Chaos (`52.3%` `2+`-Enemy Ticks):** If `K_CAP=16` still bleeds too much friendly energy after quick kills, or `K_CAP=12` suffers too many `15`-insn re-arm stuns on `50e` fronts, tune `K_CAP` via the local ablation sweep before upload.
  3. **Live Site `stun_keeps_memory` Divergence:** Verified `True` in `m9-stun-memory.txt:4` (`81.5% =4`); if an unannounced server change ever sets it `False`, `k(1..2)=1` loses its `t2` `3`-insn follow-up (falling back to `15`-insn `arm:`).
