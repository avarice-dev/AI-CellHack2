# Misfortune: build review (2026-11-13)

This is the sign-off pack for the reviewer: does the Python reference build match `briefs/misfortune-spec-2026-11-13.md`? Section letters follow the reviewer's checklist (a to h). No stage has been run. One 1000-tick game was timed (section i).

Files:

- `sim/cells_ref.py`: the Misfortune section (`misfortune_prefix`, `misfortune_pattern`, `misfortune_cap_rule`, `make_misfortune`).
- `sim/engine.py`: two measurement hooks.
- `sim/misfortune_runner.py`: the stages and the counters.
- `sim/misfortune_dump.py`: the tables in sections b and c.
- `sim/tests/test_misfortune.py` and `sim/tests/test_misfortune_runner.py`: the tests.
- `briefs/misfortune-byte-dumps-2026-11-13.txt`: the byte dumps.

## a. Spec and the decisions made in the build

The final text is `briefs/misfortune-spec-2026-11-13.md`. Its section 4 lists everything the build decided beyond the review messages:

1. The exact = 1 encoding, and its true first-bite count: 19, or 22 for cap A.
2. The cap A slot-50 store, with no branch.
3. The slow paths are v2.3a minus 1, not equal to v2.3a.
4. The pull count is padded to 80.
5. The cap B feed needs my energy >= 6.

How a boxed cell reads a neighbour: the friend's energy is the view energy of its square (`view.energies[VIEW_DIR[d]]`). Its edges are the three other squares around it, all inside the 5x5 view: UP 2/6/8, RIGHT 8/14/18, DOWN 16/18/22, LEFT 6/10/16 (`_RING` in `cells_ref.py`).

Spec point to code:

| Spec point | Code (`sim/cells_ref.py` unless named) |
|---|---|
| Layout, slot(e) = byte 13 + e, byte 8 = e0 | `MISFORTUNE_SLOT0`, `MISFORTUNE_E0` |
| Armed bite (2) | `make_misfortune`, first branch (`return a, 2, 1`) |
| Prefix (16 bytes at 9 + [8]) | `misfortune_prefix`, called first on every slow path |
| Slow paths = Bane v2.2 core + 4 | `make_misfortune`: `core = make_bane2().core`, `MISFORTUNE_PREFIX_N` |
| Arming pattern, parity, window, exact k | `misfortune_pattern` (`MISFORTUNE_LOW`, `MISFORTUNE_HIGH`) |
| Slot 50 per cap | `misfortune_pattern`, `reach` and `MISFORTUNE_CAP_A_MIN` |
| First-bite counts | `MISFORTUNE_BITE_N` |
| Cap rules A and B, feed floor | `misfortune_cap_rule` (`MISFORTUNE_RELEASE_MIN`, `MISFORTUNE_HOLD_MIN`, `MISFORTUNE_FEED_MIN`) |
| Pull count | `MISFORTUNE_PULL_N` = 80 |
| Stages, seats, log, resume | `misfortune_runner.py`: `stage_jobs`, `seat_for`, `run_stage`, `read_log` |
| Measures | `misfortune_runner.Meter` (`on_order`, `on_act`, `after_tick`, `result`) |
| Screen, choice, pass bar | `misfortune_runner.py`: `screen_lines`, `stage1_decision`, `stage2_bar`, `stage_report` |

## b. Path table

Source: `python sim/misfortune_dump.py paths` (run from `sim/`). Each cell shows the action and the instruction count. v2.3a is `make_bane3`. Its "armed bite" row has no stored bite, so it is a scan (12); its stored bite is 4.

| path | A1 | B1 | N1 | B0 | A0 | v2.3a |
|---|---|---|---|---|---|---|
| armed bite (slot set) | EAT R 2 | EAT R 2 | EAT R 2 | EAT R 2 | EAT R 2 | EAT R 12 |
| first bite (scan, arming) | EAT R 22 | EAT R 19 | EAT R 19 | EAT R 16 | EAT R 19 | EAT R 12 |
| refill (gate 1, freed square) | SPLIT D 15 | SPLIT D 15 | SPLIT D 15 | SPLIT D 15 | SPLIT D 15 | SPLIT D 16 |
| gate 1 split (e >= 16, no enemy) | SPLIT D 15 | SPLIT D 15 | SPLIT D 15 | SPLIT D 15 | SPLIT D 15 | SPLIT D 16 |
| walker move | MOVE R 38 | MOVE R 38 | MOVE R 38 | MOVE R 38 | MOVE R 38 | MOVE R 39 |
| walker blocked, settles and splits | SPLIT U 68 | SPLIT U 68 | SPLIT U 68 | SPLIT U 68 | SPLIT U 68 | SPLIT U 69 |
| settled split, first child forward | SPLIT U 42 | SPLIT U 42 | SPLIT U 42 | SPLIT U 42 | SPLIT U 42 | SPLIT U 43 |
| settled split, rotate 1 / 2 / 3 / fourth | 47 / 52 / 57 / 59 | same | same | same | same | 48 / 53 / 58 / 60 |
| prey hold (enemy on a diagonal) | REST 32 | REST 32 | REST 32 | REST 32 | REST 32 | REST 33 |
| late split (tick >= 2980) | SPLIT U 30 | SPLIT U 30 | SPLIT U 30 | SPLIT U 30 | SPLIT U 30 | SPLIT U 31 |
| threat rest (e < 5) | REST 30 | REST 30 | REST 30 | REST 30 | REST 30 | REST 31 |
| settled rest (e < 5) | REST 32 | REST 32 | REST 32 | REST 32 | REST 32 | REST 33 |
| boxed rest (e < 16) | REST 78 | REST 110 | REST 54 | REST 110 | REST 78 | REST 55 |
| boxed Schism feed | FEED U 62 | FEED U 94 | FEED U 38 | FEED U 94 | FEED U 62 | FEED U 39 |
| boxed Scourge feed | FEED U 107 | FEED U 139 | FEED U 83 | FEED U 139 | FEED U 107 | FEED U 84 |
| boxed, edge friend 48 with an empty edge | EAT U 80 (pull) | FEED U 80 (lift) | FEED U 38 | FEED U 80 | EAT U 80 | FEED U 39 |
| boxed, edge friend 48 with an enemy edge | REST 87 | EAT U 80 (hold) | REST 63 | EAT U 80 | REST 87 | REST 64 |
| boxed interior, all friends at 50 | REST 108 | REST 140 | REST 84 | REST 140 | REST 108 | REST 85 |

Against the review's expected counts:

- armed bite 2: yes.
- prefix 4: yes. It is the entry (2) plus the prefix (2).
- first bite 17: no. It is 16 at exact 0, and 19 at exact 1; cap A adds 3 (listing below).
- refill 16, walker move 39, settled splits 43 / 47-66, hold 33, late split 31: each is 1 lower here (15, 38, 42 / 47-59 plus 68 for a blocked walker, 32, 30). These expected numbers are v2.3a's. Misfortune keeps Bane v2.2's `or al, [bite_tbl + rcx]` / `jnz` at the end of the scan, while v2.3a has `mov ax, [lock2_tbl + rcx*2]` / `test al, al` / `jnz` there, which is 1 longer. Misfortune needs only the action, so the shorter form is enough.

The settled-split range here is 42-68, with the blocked walker at the top. The boxed paths with rules A and B are in the table; they do not race enemies.

Listing behind the new counts (asm not written yet; tables named only):

```
; entry: rax = 0, xmm0 = 0, esi = own energy
 1  or      al, [abs MEM + 13 + rsi]       ; slot(e)
 2  jnz     EXIT_ADDR                      ; armed bite = 2
; prefix
 3  movzx   ecx, byte [abs MEM + 8]        ; e0 of the last arming
 4  movdqu  [abs MEM + 9 + rcx], xmm0      ; zero slots e0-4 .. e0+11
; Bane v2.2 scan (cells/bane2.asm), unchanged
 5  movdqu  xmm1, [view window]
 6  pcmpeqb xmm1, [kEnemy]
 7  pmovmskb ecx, xmm1
 8  or      al, [bite_tbl + rcx]           ; EAT + d, or 0
 9  jnz     arm                            ; not taken: Bane v2.2's slow paths, each = core + 4
arm:                                       ; exact 0, cap B / N
10  mov     [abs MEM + 8], sil             ; e0
11  movzx   edx, al
12  shl     edx, 4
13  movdqu  xmm1, [pat0_tbl - 0x300 + rdx] ; one 16-byte row per direction
14  movdqu  [abs MEM + 9 + rsi], xmm1      ; slots e0-4 .. e0+11 (bytes past 63: scratch)
15  mov     byte [abs MEM + 63], 0         ; slot 50 never armed
16  ret                                    ; = 16
; exact 1: lines 11-13 become 6 (19 in all)
    movzx   edx, byte [dir_tbl - 0x30 + rax]   ; view energy offset of the target square
    movzx   edx, byte [abs VIEW + rdx]         ; te
    lea     edx, [rax + rdx*4 - 0x30]          ; te * 4 + d
    movzx   edx, byte [row_tbl + rdx]          ; d * 6 + min(5, (te + 1) // 2 - 1)
    shl     edx, 4
    movdqu  xmm1, [pat1_tbl + rdx]
; cap A: line 15 becomes 4 (+3)
    mov     dl, [abs MEM + 61]             ; slot 48
    or      dl, [abs MEM + 62]             ; slot 49
    and     dl, [a50_tbl + rsi]            ; 0xFF from e0 = 40, else 0
    mov     [abs MEM + 63], dl             ; slot 50
; cap rule action (pull, hold, lift): padded to 80 (for example a counted loop), see d.7
```

## c. Byte dumps

`briefs/misfortune-byte-dumps-2026-11-13.txt` (generated: `python sim/misfortune_dump.py dumps`) covers e0 = 1, 2, 5, 12, 39, 40 and 46-50, each direction, caps A, B and N, at exact 0 (te 20) and at exact 1 (te 5, k = 2; te 9, k = 4). Each case has two lines:

- after arming: bytes 0-63, with state bytes 03 07 00 00 1e 00 1f 00 before the call;
- after the next slow tick: at the nearest unarmed energy, in a boxed all-friend view.

Every "slow" line has bytes 9-63 zero, and bytes 0-7 as before. Three examples, bytes 8-63 only:

- cap B, exact 0, e0 1, RIGHT: `01 | 00 31 00 31 00 31 00 31 00 31 00 31 00 31 00 31 | 00 ...`. Byte 8 = 1. Slots -3, -1 and 1 to 11 odd (bytes 10-24) hold EAT RIGHT (0x31); bytes 10 and 12 are slots -3 and -1 (unused, never read).
- cap A, exact 0, e0 49, RIGHT: slots 45, 47 and 49 (bytes 58, 60, 62) and slot 50 (byte 63) are 0x31. After a slow tick at 48, all zero.
- cap A, exact 1, te 5, e0 40, RIGHT: slots 36-44 even (bytes 49-57) are 0x31, and slot 50 is 0, because the run stops at 44 and does not reach the cap.

## d. Unit tests (`sim/tests/test_misfortune.py`, `MisfortuneRefTest`: one module, no I/O)

| Test | What it proves |
|---|---|
| test_armed_bite_is_two_instructions_and_writes_nothing | For every variant and every energy 1-50, a set slot is played blind in 2 (1 without taken jumps), and memory is unchanged. |
| test_first_bite_counts | The first bite is 16 / 19 (exact 0 / 1), cap A + 3, and alt = n - 1. |
| test_armed_slots_window_parity_and_slot50 | Every e0 1-50 x direction x te (1, 2, 5, 6, 9, 20, 50) x cap x exact: armed slots match an independent spec function. They lie in e0-4 to e0+10 on e0's parity. Slot 50 is armed only with cap A, and only when the run reaches it. Byte 8 = e0. |
| test_prefix_zeroes_exactly_the_16_byte_window | For a stored e0 of 0 to 50 in all-0xFF memory, the prefix zeroes exactly bytes 9 + e0 to min(63, 24 + e0); every other byte is unchanged. |
| test_prefix_clean | For any stored e0 of 0 to 50 after an arming there (every cap), and any current energy whose slot is empty, bytes 13-63 end zero; the prefix leaves bytes 0-8 unchanged. |
| test_no_access_out_of_range | With logging memory, energies 0-50: no write below 0 or past 63, no read outside 0-63, and the first read is byte 13 + e. |
| test_every_split_leaves_child_clean | On over 1000 random split paths from an armed memory, bytes 13-63 are zero after the call, and the engine copies them to the child. |
| test_slow_paths_are_bane23a_minus_one | On 3000 random non-bite, non-boxed views (and boxed ones for cap N): the action and bytes 0-7 equal v2.3a's, and the counts are v2.3a's minus 1. |
| test_cap_rule_truth_table | Friend energy 46-50 x enemy on its edge x empty edge x puller boxed x 4 directions x my energy (4, 20), caps A, B and N, against the spec rule. Where no rule fires, the action is v2.3a's. |
| test_interior_at_50_never_eats | An all-friend interior at 50 gives no EAT under any cap. |
| test_pull_count_exceeds_every_path_of_the_pulled_cell | A pulled friend is never boxed. Every non-boxed path of every variant (random sweep, longest about 68) is below 80. |
| test_bad_flags | Bad cap or exact values raise ValueError. |

Integration tests (`MisfortuneEngineTest`, real engine, small boards):

| Test | What it proves |
|---|---|
| test_bitten_on_its_arming_tick_is_armed_at_two | Bitten first on the arming tick: on the next tick, at energy 18, the bite runs from slot 18 in 2. |
| test_run_end_after_kill_odd_last_bite | te 5: the bites take 2, 2 and 1. Counts 19, 2, 2, then a slow path at energy 25 (odd) on the tick after the kill. |
| test_run_end_after_kill_even | te 6: counts 19, 2, 2, then a slow path at 26 (above the top armed slot, 24). |
| test_cap_49_to_50 | 49 + 2 is capped to 50 at Tidy. Cap A: 22, then 2 (slot 50 armed). Cap B: 19, then a rescan at 19. |
| test_cap_n_matches_bane23a_until_first_contact | Seeds 1 and 2, 4-colony games: cap N and v2.3a (counts minus 1) give identical colony cells and energy every tick until a seat-0 cell first has an enemy on an edge. |

**Shown failing first.** The first version of these tests was written before the code and failed (13 of 13: no `make_misfortune`). After the review's corrections the code and the tests were rewritten together, so "red" is shown in two ways:

1. All 32 new tests fail against the committed code: 18 errors, because `make_misfortune`, `misfortune_prefix` and the runner module do not exist there.
2. Mutation check: 31 targeted mutations of the cell, the runner and the engine hooks (scratch script, scratch copy of `sim/`). Each mutation runs against the test meant to catch it, and 30 are caught. The one survivor is an equivalent mutant: for odd te, `te // 2` equals `(te + 1) // 2 - 1`; the even-te test catches the same mutation. Three tests were tightened after a first mutation round (exact prefix range, the 47+ threshold, the t100 check).

## e. Engine-level tests

These are listed in d (`MisfortuneEngineTest`). The determinism test is `PlayTest.test_same_seed_and_flags_give_identical_output`: the same job run twice gives identical JSON, apart from the seconds fields.

## f. Engine diff

`git diff sim/engine.py` adds only two hooks, and both are None by default:

- `order_hook(tick, acts)`: called once per tick with the sorted turn list, before any action applies;
- `act_hook(tick, cell, action, target or -1)`: called on every EAT and FEED turn, before it applies.

`cap_mid_tick` was already an engine flag (default off), so it is unchanged.

A fixed-seed game of our old cells gives an identical digest with the committed engine and with the new one: Bane v2.2, Conviction, Penalty and Bane v2.3a, seed 5, 300 ticks, digest over pop and energy per tick, the ranking and the memories. `EngineHookTest` pins that digest. It runs with and without a Meter attached, so the hooks do not change the game. Full suite: 394 tests OK (362 before, 32 new).

## g. Runner counters (`sim/tests/test_misfortune_runner.py`, `CounterTest`, real engine, scripted cells)

| Counter | Scenario |
|---|---|
| contested pair-ticks, ours first | Bites at 2 against 3: 2 contested ticks (tick 0 has no previous adjacency), ours first. At 2 against 1: ours second. |
| contested at 47+ | Our energy 47 on the contested tick: counted, and the threshold is inclusive. |
| not contested | The enemy bites elsewhere: nothing counted. |
| calls by path, contact energy | An armed bite at 49, then a rest at 50, both in contact: 'armed/2/1', 'rest/7/1', and the 47+, 49 and 50 buckets. |
| stuck episodes and end causes | feed (fed after its last stuck tick), bitten (stunned), enemy refill (an enemy moves in before the bite), friend refill (a friend moves in, and the bite counts as unintended friendly). |
| pulls, cap loss, lifts | A pull by a cell at 49 on a friend at 30: 1 pull, 1 energy lost. A padded FEED counts as a lift. Neither is unintended. |
| freed squares | A kill refilled by us on the next tick, and a kill left empty at 5. |
| checks | Cells and energy at t100 are the state after ticks 0-99 (a split on tick 100 is not counted). |
| stages | Stage job lists: 12 / 16 / 6 games (32 with --extra), the seats, the ticks and the flags. |

## h. For the final .asm (later)

These checks come when the asm exists:

- `check_cells` output;
- a Unicorn diff against `make_misfortune` over energies 0-50 x random memory x view cases, comparing the action and the per-path instruction count;
- esi on every energy-indexed access;
- the entry assumptions (rax = 0, xmm0 = 0), and that nothing on a slow path uses ecx after the prefix (the scan overwrites it);
- the contents of `pat0_tbl`, `pat1_tbl`, `row_tbl`, `dir_tbl` and `a50_tbl`;
- byte 63 per cap flag;
- that a store past byte 63 (the pattern at e0 >= 40) is allowed on the site and lands in scratch. This last point is still unconfirmed.

## i. Timing (one game, nothing else running)

Stage 1 game cap B, exact 1, seed 1, seat 0, 1000 ticks: 59.2 s. Elapsed time: 2.7 s at t100, 15.2 s at t300, 34.1 s at t600 and 59.2 s at t1000. From t300 the rate is steady at 0.063 s per tick, so a 3000-tick game takes about 3.1 min.

The figures below assume one game per core. Six parallel workers may run each game about 1.2-1.5 times slower; this was not measured.

| Stage | CPU time | Wall time, 6 workers |
|---|---|---|
| Stage 1 (12 x 1000) | about 12 CPU-min | about 2-3 min |
| Stage 2 (16 x 3000) | about 50 CPU-min | about 10-14 min (3 rounds) |
| Stage 3 (6 x 1000) | about 6 CPU-min | about 1-2 min |

That one game, as a first look only (one seed; this is not the screen):

- place 1, with 1340 cells (others 1282, 592 and 882);
- bit first on contested pair-ticks: 91.8% against Conviction (14459 of 15751), 93.7% against Bane v2.2 (34289 of 36610), 71.7% against Penalty;
- stuck: 2.0% of contact cell-ticks;
- unintended friendly bites: 4.5 per 100 enemy bites (2674 of 59446), above the 1 per 100 bar;
- cap B: 52,620 pulls, which lost 90,384 energy to the cap, and 623 lifts;
- stuck episodes 1151, ended by enemy refill 751, friend refill 183, feed 166, bitten 42 and pull 8;
- freed squares 881: ours on the next tick 16%, an enemy's within 5 81%.

## j. Deviations and doubts

1. The slow paths are v2.3a minus 1, not equal to it (section b).
2. The first bite at exact 1 is 19 (cap A 22), not 17. At 19 it ties Conviction's scan bite (19), so the tie is shuffled, and it loses to Bane v2.3a's scan (12) and to any 3-instruction queued bite. After one stunned tick the cell is armed at 2.
3. The cap-rule counts on a miss (6 or 8 per edge) are estimates. Boxed paths do not race enemies, but B's boxed paths reach 140.
4. Cap B's hold pulls are frequent, and they waste energy at the cap: in the timed game, 1.7 energy per pull. This is a design question for the screen, not a build defect.
5. "Places first" is read as place 1 in the game, which is the reviewer's "first in >= 7 games".
6. The Stage 1 tie rule, "tie or mixed sign: B", is read as follows: B, unless A's summed difference is larger and A beats B on every seed.
7. The worst single game is reported, but it is not a separate bar line.
8. The store past byte 63 is unconfirmed on the site (section h).
