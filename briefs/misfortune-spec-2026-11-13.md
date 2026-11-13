# Misfortune: final spec and test plan (2026-11-13)

Misfortune is a planned cell. Whoever bites it is bitten first on the next tick. The goal is to take and hold #1 against the current leader. The design came out of several review rounds; this file is the final text. The reference policy is `make_misfortune` in `sim/cells_ref.py`, and the build review is `briefs/misfortune-build-review-2026-11-13.md`. There is no asm yet.

## 1. Why

The first bite decides a pair, because a bitten cell loses its turn. The leader bites in 3 instructions. Bane v2.3a bites in 4 (stored bite) or 12 (scan). A 2-instruction bite is the floor of the game, so an armed Misfortune cell runs before every bite we know. A stunned call keeps its memory writes, so a cell that is bitten on its arming tick is still armed (at 2) on the next tick.

## 2. Memory layout

| Bytes | Content |
|---|---|
| 0 | bearing (Bane v2.2) |
| 1 | steps left (Bane v2.2) |
| 2-3 | unused (v2.3a's stored bite is gone) |
| 4-7 | x \| y << 16 of the last emit square (Bane v2.2) |
| 8 | e0, the energy at the last arming |
| 9-12 | unused (slots -4 to -1; the pattern store may write here at e0 <= 4) |
| 13-63 | slot(e) = byte 13 + e, for e = 0 to 50 (byte 63 = slot 50). Non-zero = an EAT action. |

Bytes above 63 are scratch and do not persist. A pattern store that reaches past byte 63 (e0 >= 40) loses only those bytes.

## 3. Paths

Entry assumptions: rax = 0, xmm0 = 0, esi = own energy. Every energy-indexed access uses rsi.

1. **Armed bite (entry).** `or al, [abs MEM + 13 + rsi]` / `jnz EXIT_ADDR`. A non-zero slot is played without reading the view: 2 instructions.
2. **Prefix (every slow path, no condition).** `movzx ecx, byte [abs MEM + 8]` / `movdqu [abs MEM + 9 + rcx], xmm0`. This zeroes the last armed window (bytes 9 + e0 to 24 + e0). So the table is zero on every slow tick, and every child is born with a clean table, because the engine copies the parent's memory after its call. If byte 8 = 0, the prefix zeroes only slots -4 to 11.
3. **Slow paths.** After the prefix come Bane v2.2's paths (`make_bane2().core`), whose scan ends with `or al, [bite_tbl + rcx]` / `jnz`. Count = core + 4. That is Bane v2.3a's count minus 1 on every slow path. See the build review, section 2: v2.3a loads action and square with `mov ax` / `test al`.
4. **Arming (an enemy beside the cell; scan bite toward d at energy e0).**
   - byte 8 = e0;
   - one 16-byte pattern store to bytes 9 + e0 to 24 + e0 (slots e0 - 4 to e0 + 11): EAT + d on the slots of e0's parity up to e0 + 10, and zero on the rest;
   - exact = 1 keeps only the slots up to e0 + 2k, where k = (te + 1) // 2 - 1 is the number of bites still needed to kill an unfed target of energy te (read at the scan). With k = 0 (this bite kills), nothing is armed;
   - slot 50 (byte 63): cap A stores `(slot 48 | slot 49) & (e0 >= 40 ? 0xFF : 0)`, so it is armed when the run reaches the cap. Cap B and cap N store 0;
   - first bite: 16 instructions at exact 0, 19 at exact 1; cap A adds 3.
   - Invariant: every armed slot lies in e0 - 4 to e0 + 10. Next-tick energy is e0 + 2 (my bite landed) - 2 per enemy bite on me, so slots -4, -2, 0 and +2 must be armed. Only one parity is armed, so the odd last bite on a 1-energy target leaves the run.
5. **Run end.** The run ends on the first unarmed slot (the top of the run or a parity change), and the cell takes a slow path: rescan, then re-arm if the target is still alive, or refill if the square is free. An exact run ends on the tick after the kill.
6. **Boxed cap rules** (ahead of Bane's boxed rules, which stay after them). An edge friend is a friend on one of my four edges. Its own edges are the three other squares around it, all inside the 5x5 view (view indices UP 2/6/8, RIGHT 8/14/18, DOWN 16/18/22, LEFT 6/10/16), and its energy is the view energy of its square.
   - cap A (release): EAT the first edge friend (order UP, RIGHT, DOWN, LEFT) at 47 or more that has an empty edge and no enemy on its edges. An all-friend interior never eats.
   - cap B: EAT the first edge friend at 48 or more that has an enemy on its edges (this holds the biter at 48, where it stays armed). Otherwise FEED the first edge friend at 47 or more that has an empty edge and no enemy on its edges (this lifts it to 50, where its slot is empty). The feed needs my energy >= 6.
   - cap N: neither (control).
   - A cap-rule action counts 80 instructions (asm: padding), above every path the pulled cell can be on (at most 68). So a pull never runs before the friend it pulls, and never stuns it. A cap rule that does not fire adds its tests to Bane's boxed count: 6 per edge for A and for B's eat pass, and 8 per edge for B's feed pass.
7. **Leftover slots** (target died early, or moved): the cell bites blind until an enemy refills the square (bitten at 2), a friend feeds it, a friend refills the square (a friendly bite), or a cap rule pulls it.

## 4. Decisions beyond the review messages

- exact = 1 is encoded as a pattern row per (direction, k) with k = min(5, (te + 1) // 2 - 1). The row index comes from a table indexed by te * 4 + d, so it costs 3 more instructions than exact = 0: first bite 19 (cap A 22), not 17.
- Cap A's slot-50 store reads slots 48 and 49 after the pattern store, which needs no branch. It arms slot 50 only from e0 = 40, so slot 50 stays inside the next prefix window.
- The slow paths are v2.3a minus 1, not equal to v2.3a. The scan keeps Bane v2.2's `or al`. The cap N engine test compares against v2.3a with its counts minus 1, so that turn order is the same.
- The cap-rule count is padded to 80, so that a pull never stuns the pulled cell.
- The feed (cap B lift) needs the puller at energy >= 6, the same floor as Schism's feed, so that a feed never kills the feeder.

## 5. Tests (staged; our own cells only, no rival model)

Line-up: the subject (Misfortune, or the control Bane v2.3a) in seat (seed - 1) mod 4; Bane v2.2, Conviction and Penalty in the other seats. Random starts. The control plays the same seed and seat. Runner: `sim/misfortune_runner.py`. It writes one JSON line per finished game and skips finished games on restart. Each stage is one command.

| Stage | Games | Content |
|---|---|---|
| 1, cap screen | 12 x 1000 ticks | caps A and B at exact 1, cap at Tidy, and the control; seeds 1-4 |
| 1n (only if both caps are out) | 4 x 1000 | cap N on the same seeds |
| 2, pass bar | 16 x 3000 | the chosen cap and the control; seeds 1-8 (2 per seat); `--extra` adds seeds 9-16 |
| 3, side checks | 6 x 1000 | seeds 1-2: exact 0 (2 games); capmid on, the new cell and the control (4 games) |

**Stage 1 screen.** A cap is out if, pooled over its 4 games, any of these holds:

- more than 1 unintended friendly bite per 100 enemy bites;
- stuck on more than 5% of contact cell-ticks;
- bit first on fewer than 90% of contested pair-ticks against Conviction, or on fewer than 95% against Bane v2.2.

Among the caps still in, the one with the larger summed (new - control) cells at t1000 wins. On a tie, or when the per-seed differences have mixed signs, the choice is B. Stop and report, with no Stage 2, if both caps are out (then run Stage 1n), or if the best cap is below the control on 3 or 4 seeds at t1000.

**Stage 2 pass bar** (n = 8; at n = 16 the same ratio, 14 of 16):

| Line | Bar |
|---|---|
| Places first | in at least 7 of 8 games |
| Above the paired control (final cells) | on at least 7 of 8 seeds |
| Bit first on contested pair-ticks | >= 90% against Conviction, >= 95% against Bane v2.2 |
| Unintended friendly bites | <= 1 per 100 enemy bites (pooled; the worst single game is also shown) |
| Stuck | <= 5% of contact cell-ticks (pooled; the worst single game is also shown) |

If either of the first two lines is exactly 6 of 8, add 8 new seeds. Bit first >= 90% against Conviction is necessary, not sufficient: Conviction is our 3-instruction stand-in, and it lacks aimed children and a checked rescan. The ladder is the first test against the rivals themselves.

**Stage 3.** exact 0 (the line-up has no feeder, which favours exact 1). Capmid on: if bit first at energy 47+ moves by more than 5 points, or stuck doubles, a site calibration probe comes before any ladder run.

**Measures per game, for the new cell and for the control:**

- cells and total energy per colony at t100, 300, 600, 1000, 2000 and 3000, and the final place;
- contested pair-ticks: our cell and an enemy cell adjacent this tick and the previous tick, both calls return EAT on the other. The share where ours ran first, per opponent, by window (< 100, 100-300, 300-1000, later), and separately for our energy 47+ at the call;
- calls by path and count, in contact and out;
- stuck: failed armed-slot eats, per armed-slot eat and per contact cell-tick. Episode length (median, p95, max) and how each episode ended (enemy refill bitten, friend refill, feed, bitten, pull);
- friendly bites, two counters: pulls by a cap rule (designed, with the energy lost to the cap) and armed-slot bites that hit a friend (unintended; this one is the bar);
- energy of contact cells: share at 47+, at 49 and at 50, by window;
- freed squares (we killed the occupant): ours on the next tick, ours within 5 ticks, an enemy's within 5, empty at 5.

The report leads with the pass-bar table (met or not met, per line), then the per-opponent numbers.
