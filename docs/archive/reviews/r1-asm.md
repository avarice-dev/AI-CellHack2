# Round 1 review: assembly feasibility and instruction-count engineering

> **Update 2026-11-08 (docs re-review).** This is a historical record; its open questions are kept as written. A later full re-read of `docs/` settled several of them: every instruction counts, including taken jumps and `ret` (Reference p.3); energy is capped at 50 in the Tidy step (Rules p.1); feed gives 2 of the feeder's energy to any cell in that direction, so "fed +3" is feed 2 + rest 1, with no bonus (Rules p.1-2); a square freed by a death opens next tick, one freed by a move opens the same tick (Rules p.2); matches are deterministic from the seed (Rules p.3); SSE2 and SSE3 are available (Reference p.3); loops, the stack and `[rdx]` memory are allowed by the game. Ladder starts are not corners (replays; the Rules never say corners). See `architecture/overview.md` for the current summary.

Lens: x86-64 NASM implementation, instruction counts, test harness. Counts assume every executed
instruction (including `ret`, taken jumps, indirect jumps) is 1, same as designs.md. Rules read from the
docs (PDFs converted to text) and cellhack.inc.

## 0. Facts from the docs that the draft under-uses

- `VIEW_COLONY` (u8, 0..3) is free in the view. Home corner = f(colony slot), so no init code, no flags
  byte, no home-corner byte. Verify the slot-to-corner mapping once in the sandbox.
- Unused view bytes are zero. A 16-byte load running past idx 24 (VIEW_CELLS+16 .. +31, VIEW_ENERGIES+16 ..
  +31) reads zeros and never faults (view page is 4 KB mapped).
- VIEW_CELLS (32), VIEW_CELLS+16 (48), VIEW_ENERGIES (64), +16 (80) are 16-byte aligned, so legacy-SSE memory
  operands (`pcmpeqb xmm0,[rdi+32]`) are legal there. A window starting at any other idx (e.g. idx 7 = byte
  39) needs `movdqu` into a register first. A non-VEX SSE ALU op with an unaligned m128 operand raises #GP =
  a fault every call = a dead colony. This is the single most likely catastrophic bug.
- Code is mapped at 0x100000 (16-byte aligned), read+exec, 64 KB padded with int3 (0xCC), 32 KB max blob. So
  `align 16` data tables inside the blob are legal to read. Falling into padding = int3 = fault. An unfilled
  table byte read as an action = 0xCC = bad_action fault.
- qemu64: SSE2/SSE3 only. NOT available: SSSE3 (`pshufb`, `pmaddubsw`), SSE4.1 (`phminposuw`, `pmaxsb`),
  `popcnt`, BMI/`tzcnt`/`lzcnt`. `bsf`, `bsr`, `bt`, `cmov`, `setcc`, `imul`, `pextrw`, `psadbw`,
  `pmovmskb` are fine.
- Wall = 3 and enemy = 2 both have bit 1 set, so a cheap `psllw 6; pmovmskb` enemy test false-fires on
  walls (border cells would eat walls forever). Use `pcmpeqb` with a constant.

## 1. Section 1.2 instruction counts

### 1.1 Verdict on the draft's rows

| Row | Draft | Verdict |
|---|---|---|
| Static `cmp/je` x4 | 4/6/8/10 | Correct (enemy in 1st/2nd/3rd/4th checked direction); miss-all = 8 then continues. |
| SSE2 mask, 7 flat | 7 | Correct as written, but beatable: 6 flat (or 5 with a REST fallback), see 1.2. `pcmpeqb xmm0,[mem]` needs an aligned constant (draft does not say). `and eax,0x451` can be removed. |
| Mode dispatch +2 | +2 | Correct for `movzx`+`jmp [tbl+rax*8]`. A form that returns directly with the same +2 exists, see 1.3. |
| `jmp [rdx]` faults on zeroed memory | yes | Correct (rip=0 unmapped). No 1-instruction safe dispatch exists; cheapest safe mode check is 2. |
| Locked blind eat | 4 | Correct for table dispatch; 3 with the `or al,[rdx]` form (1.3). |
| Locked checked eat | 6 | Correct, but a stateless SSE front is also 6 and needs no state, so the checked lock buys nothing. |
| Branchless post | 5 | Correct for that form; dominated by the stateless 5 in 1.2. |

### 1.2 Cheaper stateless front (no memory state, no mode)

Constants (aligned, in the code region after the last `ret`). Window starts at idx 7 so lanes 0,4,6,10 are
UP(7), LEFT(11), RIGHT(13), DOWN(17). Junk lanes hold 0xFF, which never equals a cell type 0..3, so they can
never match. This removes the draft's `and eax,0x451`:

```
align 16
kEnemy: db 2,255,255,255, 2,255,2,255, 255,255,2,255, 255,255,255,255   ; mask bits 0,4,6,10
kEmpty: db 0,255,255,255, 0,255,0,255, 255,255,0,255, 255,255,255,255
```

Variant F6 (6 on an enemy hit, 4 on a miss; jump table; the miss target is just the continuation of the
program so the miss costs nothing extra):

```
movdqu   xmm0, [rdi+VIEW_CELLS+7]   ; 1
movdqa   xmm1, xmm0                 ;   (only needed later for the empty mask; not on the F6 path)
pcmpeqb  xmm0, [kEnemy]             ; 2   aligned constant
pmovmskb eax,  xmm0                 ; 3   eax in {0x000..0x451}, zero-extended into rax
jmp      [fight_tbl+rax*8]          ; 4   absolute disp32 (an index register => `default rel` does not apply)
...
.eatU: mov al, ACT_EAT+DIR_UP       ; 5
       ret                          ; 6
```
`fight_tbl` is 1106 qwords = 8.8 KB, only 16 entries reachable: fill the rest with a pointer to a safe
`xor eax,eax / ret`, never with zero (a zero entry jumps to address 0 = fault). Entry 0 = non-fight
continuation. Multi-enemy masks can point at a longer handler that compares energies (2.1) while
single-enemy masks stay at 6. Tie priority between directions is encoded in the table for free.

Variant F5 (flat 5, byte table, REST fallback, no branch):
```
movdqu / pcmpeqb / pmovmskb eax / mov al,[act_tbl+rax] / ret      ; 5, act_tbl[0] = ACT_REST
```
`act_tbl` is 1106 bytes. This is a complete cell ("eat an adjacent enemy, else rest") in 5 instructions with
no state. It cannot also grow, because no flag-setting instruction sits between the table load and `ret`
(`mov al,[..]` leaves flags alone). Use it as the yardstick.

Enemy-adjacent path, single enemy:

| Technique | Up | Right | Down | Left | Miss (continue) |
|---|---|---|---|---|---|
| Static order U,R,D,L | 4 | 6 | 8 | 10 | 8 |
| Draft SSE (and + jz + byte table) | 7 | 7 | 7 | 7 | 5 |
| F6 (jump table) | 6 | 6 | 6 | 6 | 4 |
| F5 (byte table, REST fallback) | 5 | 5 | 5 | 5 | n/a (rests) |

Static-first-then-F6 only helps if the cell knows which direction its front faces; one program serves all four
slots, so that needs colony dispatch (+2) for a 2-instruction gain on one direction. Not worth it.

Rejected alternatives:
- `xlat`: needs rbx = table (extra setup) and an 8-bit index; bit 10 of the mask does not fit. No gain over
  `mov al,[tbl+rax]`.
- `psadbw` weighted sum to produce the action byte directly: two enemies sum to garbage = fault; 6 instr anyway.
- `cmov`/`setcc` chains: about 3 instructions per direction, worse than the table.
- `psllw` replacing `pcmpeqb`: saves the memory constant but false-fires on walls.
- Packing empty and enemy masks into one key (second compare, `pslldq`, `por`): 9 instructions, no gain.
- The sparse key (bits 0,4,6,10) makes tables 1106 long. Fine for 32 KB: F6 table 8.8 KB plus about 1.1 KB per
  byte table.

### 1.3 Mode dispatch / lock safe on zeroed memory

Required property: the root's first call sees `[rdx..rdx+63]` all zero and must reach the default logic.

| Form | Default path cost | Locked path | Needs |
|---|---|---|---|
| `movzx eax,byte [rdx]` / `jmp [mode_tbl+rax*8]` | +2 | 2 + handler (`mov al,imm`, `ret`) = 4 | nothing; table entry 0 = default |
| `cmp byte [rdx],0` / `jnz .locked` | +2 | 2 + `mov al,[rdx]` + `ret` = 4 | nothing |
| `or al,[rdx]` / `jz .full` / `ret` | +2 (jz taken) | 3 | rax = 0 at entry (draft 1.3 asks; docs say registers are reset; verify) |
| `jmp [rdx]` | n/a | faults on zero memory | not usable |

The `or al,[rdx]` form stores the final action byte in memory ([rdx+0] = 0x30+d, 0 = unlocked). Zero memory is
automatically "unlocked" and the locked path is `or / jz / ret` = 3. If rax is not guaranteed zero it costs +1
(`xor eax,eax` first) and the locked path is 4.

Exit rules and their real cost:

| Lock | Locked path | Behaviour |
|---|---|---|
| Blind | 3 | Eats a dead square (no-op) or a friend that stepped in, forever: a locked cell never reaches the full path, so nothing can reset it. Needs an external exit. |
| TTL counter | `or al,[rdx]` / `jz` / `sub byte [rdx+1],1` / `jz .expire` / `ret` = 5 | Bounded waste of N ticks, then re-evaluates (that tick costs full-path instructions, so initiative is lost that tick). |
| Tick-mask | `or al,[rdx]` / `jz` / `test byte [rdi+VIEW_TICK],3` / `jz .full` / `ret` = 5 | Same idea, no write. |
| Checked | `or al,[rdx]` / `jz` / `movzx ecx,byte [rdx+1]` / `cmp byte [rdi+rcx],CELL_ENEMY` / `jne .full` / `ret` = 6 | ([rdx+1] = VIEW_CELLS+idx of the target.) Equals the stateless F6, with state. |

Conclusion: the checked lock is pointless (F6 is 6 with no state). TTL/tick lock saves 1 over F6 at the price
of periodic initiative loss and bugs. Only the blind 3-4 lock is a real gain (2-3 instructions), and it is the
dangerous one. Ship F6 first. Add a lock only if measurements show Hunter's (and ladder rivals') front path is
at or below 6. Hunter's exact eat path can be counted from hunter.asm on the site; the match page also reports
average and maximum instructions per call.

Tax of the lock prefix: `or al,[rdx]` + `jz` = +2 on every unlocked path, so an unlocked front cell is 8
instead of 6 on the first contact tick, then 3 once locked.

### 1.4 Other places where instruction count matters

- Interior cells never contest initiative except for races on the same empty square (split/move), so their
  length does not matter beyond budget (1000) and the last tie-break (total instructions over the match).
- A `nop` pad is a legal tool to make a cell act later on purpose (a feeder that should act after the cells
  that eat; a mover that wants a square vacated earlier in the tick). Only Reaper might want it.
- Counting convention (ret, taken jumps, `rep`) is unknown; compare designs against each other only until it is
  calibrated (section 4).

## 2. Per-design estimates

Common kernel assumed: F6 front (6), colony-indexed split/rest tables, `cmp esi,5` gates, no loops. Numbers
are executed instructions on the named path.

### 2.1 Design A "Bastion"

| Path | Draft | Estimate | How |
|---|---|---|---|
| Front eat, 1 enemy | 4-10 | 6 | F6. |
| Front eat, 2-4 enemies, prefer <= 2 energy | stated | 14-20 | Handler: `movdqu xmm2,[rdi+VIEW_ENERGIES+7]`, `pcmpgtb` against a register holding 3 (`movdqa xmm3,[k3]`), `pand` with the enemy mask, `pmovmskb`, table. Only the multi-enemy case pays. |
| Expansion split (e>=5, no enemy within 5x5) | not stated | 10-14 | F6 miss 4, `cmp esi,5`/`jb`, `pcmpeqb xmm1,[kEmpty]`, `pmovmskb ecx,xmm1`, colony row (`movzx edx..` / `shl ecx,11`), `mov al,[tbl+rcx+rax]`, `ret`. (rdx must be preserved if used for memory; use another register.) |
| Prey rule / threshold 5 vs 16 | not stated | +7 | "Any enemy anywhere in 5x5": `movdqu x0,[rdi+32]`, `movdqu x1,[rdi+41]` (idx 9..24), `pcmpeqb` x2 vs all-2 constant, `por`, `pmovmskb`, `test`, `jnz` = 7. Idx 12 (self) must not read as enemy; verify. |
| Feed (e>=20, friend poorer by >=4) | not stated | 22-30 | Broadcast energy (`imul eax,esi,0x01010101`; `movd xmm2,eax`; `pshufd xmm2,xmm2,0` = 3), load energy window, `pcmpgtb` vs (e-3), friend mask `pcmpeqb`, `pand`, `pmovmskb`, table -> `ACT_FEED+d` or fall through. "Poorest" has no horizontal min in SSE2 (no `phminposuw`), so you get first-eligible by table priority, which is fine. |
| "Friend that touches an enemy gets priority" | stated | +20-30, doubtful | Needs the ring-2 view per direction (3 cells each). Drop it: a front friend is the poorest anyway, so the margin rule already routes feed to the front. |
| Rest | cheap | 9-12 | F6 miss, empty compare, gates, `mov al,ACT_REST`, `ret`. |

Fault risks: misaligned SSE memory operand (all of A depends on it); unfilled table entries (0xCC read as an
action, or a zero jump-table entry); colony row index (VIEW_COLONY 0..3: size the tables for 4); writing to the
view (read-only). No loops, so budget is not a risk: worst path under 70.

Complexity: 150-250 lines is realistic only with generated tables (the 1106-entry tables are not
hand-writable); hand-written part is about 150 lines.

### 2.2 Design B "Tide"

| Path | Estimate | Notes |
|---|---|---|
| Front eat | 6, or 8-9 with sensing writes | Storing last action/energy on the hot path costs `mov [rdx+5],al` (+1) plus an energy store (+1-2). Keep all stores off the front path; store only on non-front paths. |
| Local strength (friend minus enemy energy, 5x5) | 18-24, not 10-14 | Cells lo/hi (aligned; hi's 7 trailing bytes are zero), energies lo/hi, 2x `pcmpeqb` enemy, 2x `pand`, `paddb` merge (disjoint lanes, <= 100 per byte, no overflow), `pxor`, 2x `psadbw` (total and enemy), add halves (`pshufd`/`psrldq` + `paddq`, or `pextrw` words 0 and 4), then T - 2E. About 13 for the SSE part, 6-8 to extract and combine. Slow path only. Self energy is in T. |
| Push/hold decision | +10-15 | POP_SELF/POP_ENEMY thresholds: `movzx` x2, `lea`, `cmp`, `cmov`. Cheap. |
| Initiative sensing | +8-10 | Two loads, compare, saturating update. |
| Whole slow path | 40-70 | Well inside 1000. |

Risks: sensing is noisy (energy delta mixes my own bite, bites by other enemies, feeds, rest) and stun is not
directly observable. A cleaner signal is the adjacent enemy's energy trend (needs a stored previous value per
direction). A child inherits the parent's last energy/action, faking a delta on its first tick (guard with
VIEW_AGE == 0, +2). 300-450 lines is realistic if sensing stays simple.

### 2.3 Design C "Reaper"

| Path | Estimate | Notes |
|---|---|---|
| Locked eat (blind, `or al,[rdx]`) | 3 | Only valid with an exit; see 1.3. |
| Locked eat (TTL / tick mask) | 5 | |
| Unlocked front cell (first contact, sets lock) | 8 + store = 9-10 | Lock-prefix tax 2 + F6 6 + 1-2 writes. |
| Mode dispatch (non-front, second level) | +2 | Put the mode jump on the slow path only, after the F6 miss. The draft's "+2 on every path" is avoidable. |
| Raider step: nearest enemy in 5x5 | 20-28 | 25-bit enemy mask (two `pcmpeqb`, two `pmovmskb`, shift/or), `and` ring-1 then ring-2 masks, `bsf` (branch on ZF; dest undefined when source is 0), `mov al,[dirtbl+rax]` over 25 entries. |
| Pincer logic | 30-50 | Geometric; the draft is vague. |
| Whole slow path | 60-100 | Within budget. |

Fault/behaviour risks: blind lock eats an empty square (no-op, wasted tick) or a friend (damage to own
colony); lock byte inherited by a child (a parent that sets the lock and splits in the same call copies it:
write the lock after the split decision, or clear it in the child's first call); a mode byte beyond the table
jumps into int3 padding; a move into an occupied square does nothing (not a fault). 400-600 lines is
realistic. The lock gain (6 -> 3) is the weakest part of the case for C.

## 3. Proposed code structure and memory layout

### 3.1 Memory (64 persistent bytes, zero = default for everything)

| Offset | Use | Owner |
|---|---|---|
| 0 | Lock action byte: 0 = unlocked, else the exact action to return. Read by `or al,[rdx]`. | C only (A/B keep 0) |
| 1 | Lock TTL / age | C |
| 2 | Role/mode (0 = default, 1 = raider, ...) | C |
| 3 | Flags | all |
| 4 | Last energy | B |
| 5 | Last action | B |
| 6 | Initiative score (small signed int) | B |
| 7 | Spare | |
| 8..15 | Per-lineage scratch | |
| 16..63 | Design specific | |

No home-corner byte: use VIEW_COLONY. No init flag: nothing needs initialising because zero is meaningful.
Everything the hot path needs lives in the view, not in memory.

### 3.2 Code layout (one flat blob)

```
entry (offset 0):
   [C only: or al,[rdx] / jz .full / ret]
.full:
   movdqu xmm0,[rdi+VIEW_CELLS+7] ; movdqa xmm1,xmm0 ; pcmpeqb xmm0,[kEnemy] ; pmovmskb eax,xmm0
   jmp [fight_tbl+rax*8]                      ; mask 0 -> .nofight
.eatU .eatR .eatD .eatL: 2 instructions each
.multi: weakest-first handler
.nofight:
   endgame check (cmp dword [rdi+VIEW_TICK], END-20)
   enemy-in-5x5 flag (7 instr, only if the prey rule is on)
   split via colony-indexed tables, feed, rest
(end of code)
align 16
kEnemy kEmpty k2 k3 ...                       ; SSE constants
align 16
fight_tbl: dq ...                             ; generated
act_tbl / split_tbl (4 rows x 2048)           ; generated
```
Tables are a pure function of the 4-bit mask: a 40-line Python generator emits them. The server prepends only
the constants and rejects `%include`-style dependencies, so flatten with `nasm -e` and upload the result.

### 3.3 Sharing one kernel across A, B, C

- One kernel file with `%ifdef DESIGN_B` / `%ifdef DESIGN_C`. Macros: `LOAD_NEIGH`, `ENEMY_MASK`,
  `EMPTY_MASK`, `GATE_ENERGY n, label`.
- A = kernel only. B = A plus the strength block, hooked after the F6 miss and before the split decision.
  C = A plus the lock prefix at entry and mode dispatch on the slow path. The F6 front is stateless, so the
  three designs have identical front timing except C's lock prefix: any ladder difference from the front is
  attributable to the lock.
- Same generator for all three; each design only changes the small action tables.

### 3.4 Hot-path rules

1. Anything that writes memory stays off the F6 path.
2. Slow-path code is entered only after the F6 miss, with `xmm1` still holding the raw window for reuse.
3. Every table fully initialised (generated lines or `times N db`); every handler returns a valid action;
   unreachable keys go to `xor eax,eax / ret` (NOP is legal).
4. No loops anywhere (budget then irrelevant); use ring masks plus `bsf` instead.
5. Do not rely on any register or xmm value at entry other than rdi/rsi/rdx/rsp (the one deliberate exception,
   `or al,[rdx]`, is to be verified first).

## 4. Test plan item 2 (Python engine + Unicorn + NASM on Windows)

### 4.1 Feasibility

- `pip install unicorn` has Windows amd64 wheels (2.x); NASM installs with scoop/winget. Nothing needs Linux.
- Unicorn's default x86-64 CPU model is qemu64, the model the docs name, so SSSE3/popcnt fault the same way.
  The real engine is probably Unicorn/QEMU-based, so counting semantics likely match a `UC_HOOK_CODE` counter.
- Memory protections map directly: code R+X (0x100000, 64 KB filled with 0xCC), stack RW (0x200000, 16 KB;
  leave neighbours unmapped for guards), view R (0x300000), cell mem RW (0x310000), `until` = 0x400000 (stop
  when pc reaches EXIT_ADDR; leave it unmapped or stop before executing). A write to code/view gives
  UC_ERR_WRITE_PROT. `int3` raises an error; catch it as a fault = NOP.

### 4.2 Speed

4096 cells x 3000 ticks, but the board fills in the first few hundred ticks: about 9-12 million cell calls per
match. Per call in Python: build the view (128 B from a numpy grid), write mem 64 B, set rdi/rsi/rdx/rsp, push
the return, `emu_start`, read al and 64 B back: roughly 30-60 microseconds without a hook. A Python
`UC_HOOK_CODE` callback adds about 1-3 microseconds per instruction x 10-14 per call, 15-40 microseconds more.
Net: 10-25 minutes per full-size match, single thread. Too slow for tuning loops, fine for a few final
validation runs, and parallelisable (all cells decide on the same snapshot before any action, so cells can be
split across processes, each with one reused Unicorn instance; never create an instance per call).

Mitigations if kept: (a) develop on 32x32 / 600 ticks (about 0.5M calls, about 1 minute); (b) hook only code
addresses you must count; (c) `UC_HOOK_BLOCK` plus a Capstone-precomputed instruction count per translation
block (about 4x fewer callbacks), validated against the per-instruction hook on random inputs because block
boundaries can be subtle; (d) a C or Rust harness using the Unicorn C API, 20-50x faster than Python callbacks.
Memoising calls keyed on the inputs is not worth it (rand, tick, age, x, y vary per call).

### 4.3 Pitfalls when matching the real engine

1. Counting convention: does `ret` count, do taken jumps, how are `rep movs/stos` counted (Unicorn typically
   fires the code hook per iteration), is the budget check `> 1000` or `>= 1000`. Unknown until calibrated.
   Cells should not use `rep`.
2. Initial register state: rax, rcx, r8-r15, xmm0-15, flags. The `or al,[rdx]` lock depends on rax = 0.
3. Whether a faulting call's partial writes to [rdx] persist.
4. When memory is copied to a child (at SPLIT time using the parent's end-of-call memory?). Matters for any
   lock/mode/score byte.
5. Action semantics from the rules page: decide all cells on one snapshot, sort by (instruction count, random),
   apply in order; a bite after a move hits the newcomer; a dead cell keeps its square until Tidy; squares
   vacated earlier in the tick can be entered; stun applies only to cells that have not acted; cap at Tidy;
   split rounding unknown (draft 1.3).
6. Randomness cannot be reproduced bit-for-bit (PRNG and seed unknown): the harness can be compared to the site
   only in aggregate, not replay by replay.
7. Assembly parity: prepend exactly `bits 64 / org CODE_BASE / default rel / <cellhack.inc>`, assemble with
   `nasm -f bin -w+all`, check size <= 32 KB, scan for forbidden mnemonics with Capstone. Verify that a
   misaligned `pcmpeqb xmm0,[odd]` faults in the harness.
8. Stack zeroing is only needed if a cell reads uninitialised stack; ours do not, so skip it for speed but keep
   the return address at STACK_TOP-8.

### 4.4 Simpler alternative (recommended)

1. **Differential test of the asm cell against a Python reference of the same logic**: inputs = all 4^4
   neighbour type combinations x energy ranges x memory states, plus edge cases (walls, all-empty, root with
   zero memory, rand extremes). About 1e5 Unicorn calls = seconds. Compare action, memory after, instruction
   count, fault status.
2. **Strategy simulation with the Python reference cells only** (no emulation), using the path-tagged
   instruction counts validated in step 1. A pure-Python cell call is 3-8 microseconds; a full match is 1-2
   minutes, or seconds with NumPy-vectorised neighbour logic. Bots are re-implemented in Python from their
   published source with their own measured counts (read from the site's per-call average).
3. **Site sandbox for ground truth**: counting convention, split rounding, start squares, rax at entry, slot to
   corner mapping, memory copy timing. Calibration cells: `mov al,1 / ret` (reports 1 or 2 average); a cell with
   a deliberate fault if rax != 0 (visible in the fault log).

Unicorn stays off the hot loop, iteration is fast, and the asm is still proven equal to the model.
