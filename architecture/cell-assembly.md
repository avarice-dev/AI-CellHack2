# Cell assembly: the instructions and the reasons for them

This document explains the x86-64 assembly in the CellHack2 cells: which instructions they use, why, and how each decision is coded. You do not need to know assembly. The [glossary](#glossary) defines the terms. Game rules are in [overview.md](overview.md). The history of each cell is in [cells-and-experiments.md](cells-and-experiments.md).

## The short version

A cell gets one turn in each tick and returns one action. A cell that runs fewer instructions acts earlier in the tick, and an earlier turn can win a contested square. Speed is the main design goal.

To keep the turn short, the cells use a **one-step lookup**. The cell copies part of its view into a 16-byte register, compares all 16 bytes with one instruction, and packs the result into a number called a mask. The mask is an index into a table that holds the answer. The site accepts only some instruction sets, so the project tested each set before it used it.

## Why instruction count matters

Within a tick, cells run in order of instruction count, lowest first. The count includes every instruction run, each taken jump and the final `ret`, the instruction that ends the call. All colonies share one pass per tick. The match seed orders equal counts, so a match with the same seed replays identically (Rules, pages 2 and 3; Reference: "The engine counts every instruction."). A probe with a `mov` and a `ret` averaged 2 instructions per call on the site.

A call over 1000 instructions (`INSN_BUDGET` in `docs/cellhack.inc`) is a fault, and the cell does nothing that tick. The longest path in Covetous is 60 instructions, and in Scourge 53. The cap does not limit these cells.

A square freed by a death cannot be entered until the next tick. A square freed by a move can be entered later in the same tick. Two cells cannot swap places. The race for a freed square is therefore decided by turn order in the next tick. The total instruction count also breaks ties at the end of a match, after population and total energy (Rules, page 2).

## The core trick: one compare, one lookup

A register is a small storage slot in the processor. The cells use general registers such as `rax`, and 16-byte registers `xmm0` to `xmm15`, which belong to the SSE instruction family.

The game passes a pointer to the view in `rdi`. The view holds 25 bytes, one per square of the 5 by 5 block, in row order. The cell is at index 12. Index 7 is up, 11 left, 13 right, 17 down. This is the bite from `cells/covetous.asm`, which every later cell reuses:

```nasm
start:
	movdqu		xmm0, [rdi + VIEW_CELLS + VIEW_UP]	; view idx 7..22
	pcmpeqb		xmm0, [kEnemy]
	pmovmskb	ecx, xmm0			; bits 0 UP, 4 LEFT, 6 RIGHT, 10 DOWN
	or		al, [abs bite_tbl + rcx]	; rax = 0 at entry: al = eat action, ZF = no enemy
	jnz		EXIT_ADDR			; bite: leave through the return address
```

1. `movdqu` copies 16 bytes from the view into `xmm0`. It works at any address (`u` = unaligned).
2. `pcmpeqb` compares 16 pairs of bytes. Equal bytes give 0xFF, others 0. `kEnemy` holds the enemy value 2 in the four neighbour positions and 0xFF elsewhere. No square has the value 0xFF, so those positions never match.
3. `pmovmskb` packs the top bit of each byte into `ecx`. This is the mask: bit 0 UP, bit 4 LEFT, bit 6 RIGHT, bit 10 DOWN.
4. `or al, [abs bite_tbl + rcx]` reads the table entry for the mask. `abs` fixes the table address when the file is built.

Example: mask 0x411 has bits 0, 4 and 10 set, so enemies stand UP, LEFT and DOWN. With three enemies, the rule is to bite the side opposite the free side, which is LEFT. The table entry is 0x33: 0x30 means bite, and 3 means LEFT.

The bite table has 1106 entries, one per mask value from 0 to 0x451. The generator fills every entry. A lookup costs one read, whichever squares hold enemies. A chain of if-statements would cost a compare and a jump per case.

## The five-instruction bite

The bite is the five lines above. The first three build the mask, the fourth reads the answer, and the fifth leaves if there was a bite.

The `or` also sets the zero flag. A mask with no adjacent enemy points to a zero table byte, so the zero flag is set and the cell goes on to the code below the bite (the slow path). A miss costs the same 5 instructions as a hit.

`jnz` jumps when the zero flag is clear, to `EXIT_ADDR`, the address that a `ret` would return to. The call ends there and skips the `ret`, which saves one instruction.

The design notes call this bite F5: 5 instructions in every direction, no memory. The strongest rivals bite in about 4 in one fixed direction, about 6 in a second, and 8 or more in the others. F5 beats every rival's second direction and every slower side.

Four facts make the bite safe:

- The `or` needs `al` to be zero at entry. Probe `c_rax_probe` found `rax` zero on every call.
- The bite overwrites `xmm0` and `ecx` before it reads them. Probes `r_gpr_zero` and `q_xmm_zero` also found `rbx`, `rcx`, `rbp`, `r8` to `r15` and `xmm0` to `xmm15` zero at entry.
- The `jnz` exit needs the site to treat a jump to the return address like a `ret`. Probe `e_jexit` confirmed this, with 2 instructions per call and no faults.
- The jump leaves the stack pointer 8 bytes lower than a `ret`. The game resets the stack before every call.

## Splitting, and the energy threshold

A split creates a child on an empty neighbouring square. The code uses the same pattern, with a constant that marks empty squares:

```nasm
split:
	movdqu		xmm0, [rdi + VIEW_CELLS + VIEW_UP]
	pcmpeqb		xmm0, [kEmpty]
	pmovmskb	eax, xmm0			; bits set = empty adjacent squares
	test		eax, eax
	jz		feed
	mov		al, [abs split_tbl + rax]	; non-zero mask -> a split
	ret
```

`test` sets the zero flag when the mask is zero, and `jz` then goes to the feeding code. Otherwise the table gives the split direction. Before this code runs, the cell must have enough energy. Covetous decides the threshold with a 5x5 check:

```nasm
	cmp		esi, SPLIT_MIN
	jb		rest
	movdqu		xmm1, [rdi + VIEW_CELLS]	; view idx 0..15
	movdqu		xmm2, [rdi + VIEW_CELLS + 9]	; view idx 9..24
	pcmpeqb		xmm1, [kTwoLo]			; lane 12 (self) never matches
	pcmpeqb		xmm2, [kTwoHi]			; lane 3 (self) never matches
	por		xmm1, xmm2
	pmovmskb	eax, xmm1
	test		eax, eax
	jnz		threat
```

`esi` holds the cell's energy. A cell below 5 energy rests. The 25 squares do not fit in one 16-byte window, so the cell uses two overlapping windows and joins them with `por`. The constants keep the cell's own square out of the result.

| Situation | Threshold | Reason |
|---|---|---|
| Ordinary play | 5 | `SPLIT_MIN` in `docs/cellhack.inc`. |
| Enemy anywhere in the 5x5 view | 16 | The prey rule: a child near an enemy must get at least 8 energy. |
| From tick 2980 | 5 | Endgame rule: fill every empty neighbour. |

## Feeding from full cells

Feeding gives 2 of the feeder's energy to the cell in the chosen direction. A feeder with less than 2 gives all it has, and dies if that was all. The target can be an enemy, so the cells check for a friend first. A cell near the cap of 50 gains little from resting, so it gives energy away at little cost. In Covetous, a cell at 47 energy or more feeds its poorest friend neighbour, if that friend has 46 energy or less:

```nasm
feed:
	cmp		esi, 47
	jb		rest
	mov		r8d, 255			; poorest friend energy so far
	mov		eax, ACT_REST
	cmp		byte [rdi + VIEW_CELLS + 7], CELL_FRIEND	; up
	jne		.n_up
	movzx		ecx, byte [rdi + VIEW_ENERGIES + 7]
	cmp		ecx, r8d
	jae		.n_up
	mov		r8d, ecx
	mov		al, ACT_FEED + DIR_UP
```

`r8d` keeps the lowest friend energy so far. It starts at 255, so the first friend always wins. The block repeats for right, down and left. A target at 47 or more gains little. One rival, Aegis, wasted 34% of its feeds on full cells. Scourge's feeding floor is 16 energy, and Contagion's is 12.

## The refill gate in Scourge

A freed front square is an empty neighbour with an enemy beyond it or beside it. Scourge tries to retake these squares right after the bite fails:

```nasm
slow:						; 5 instructions so far
	movdqu		xmm1, [rdi + VIEW_CELLS + 6]	; view idx 6..21
	pcmpeqb		xmm1, [kRefill]			; empty neighbours, enemies beside/beyond them
	pmovmskb	ecx, xmm1			; mask 0..7607
	mov		al, [abs act_tbl + rcx]		; split to take (0 = no empty neighbour)
	cmp		sil, [abs thr_tbl + rcx]	; energy it needs (12 refill, 16 other, 255 boxed)
	jae		EXIT_ADDR			; refill / split: 11 instructions
```

The window starts at view index 6. `kRefill` marks the four neighbours as empty and six more squares (the diagonals and the squares two steps left and right) as enemies. The mask reaches 7607, so the table has 7,608 entries.

`act_tbl` gives the split direction for the mask. `thr_tbl` gives the energy that split needs: 12 for a refill, 16 for a normal split, 255 for a boxed cell (no empty neighbour), which can never split. `cmp sil` compares the energy with that number, and `jae` leaves when it is enough.

The path is 11 instructions: 5 for the bite and 6 lines above. Only the VEX variants reach 10, and they are broken on the site.

A parent with 12 energy gives its child 6. AtomPush's children were 5 to 7 energy in the replay study.

The window stops short of squares 2 and 22, the squares beyond UP and DOWN. Indexes 2 to 22 need 21 bytes. Reading them would cost at least 3 more instructions on the path that has to stay fast.

Scourge refilled 98% of the squares that its rivals ate from it in the ladder study.

## The prey hold, and why Complacency drops it

Covetous and Scourge rest instead of splitting when they have 5 to 15 energy and an enemy is anywhere in the 5x5 view, until tick 2980. This is the Scourge code:

```nasm
threat:
	cmp		dword [rdi + VIEW_TICK], 2980
	jae		EXIT_ADDR			; late: split anyway
rest:
	mov		al, ACT_REST
	ret
```

Scourge lost the land grab: at tick 200 it had about 800 cells on the ladder, and the winners about 2400. Complacency is Scourge with the hold removed. Its middle split is a plain split at 5 energy or more, with no 5x5 check. That path costs 16 instructions, against 24 to 27 on Scourge's same paths:

```nasm
	cmp		esi, 5
	jb		rest
	ret					; split: no prey hold
rest:
	mov		al, ACT_REST
	ret
```

The simulator sweep tested a hold that stops at tick 200, 300, 500 or never, and a hold only for a diagonal enemy. "Never" gave the highest final population in all three mixes, with equal win rates, and it is the simplest code. Head-to-head numbers on new seeds followed the start slot, not the cell.

Pull 5 shows that dropping the hold did not close the grab gap. Complacency reaches 128 and 512 cells at t36 and t84. AtomPush reaches them at t29 and t63. The gap comes in the first 35 ticks, and `designs.md` 10.2 traces it to the geometry of the split direction. Schism (`designs.md` 10.4) tests this.

## Constraints and what was ruled out

The site runs a limited set of instructions. Probe cells in `cells/calib/` tested each set:

| Instruction or set | Result on the site | Probe |
|---|---|---|
| SSE2 basics, such as `movdqu`, `pcmpeqb`, `pmovmskb`, `por` and `pxor` | Works, and the cells use them | Used in the cells |
| `popcnt` | Invalid-instruction fault on every call | `f_popcnt` |
| `pshufb` (SSSE3) | Not supported | `g_ssse3` |
| `ptest` (SSE4.1) | Not supported | `h_sse41` |
| `crc32` (SSE4.2) | Not supported | `m_sse42` |
| `andn` (BMI1) | Not supported | `i_bmi1` |
| `pext` (BMI2) | Not supported | `j_bmi2` |
| 256-bit AVX2 (`ymm` registers) | Not supported | `l_avx2` |
| VEX `vpshufb` | Not supported | `n_vex_pshufb` |
| VEX `vptest` | Not supported | `o_vex_ptest` |
| 128-bit VEX `vpcmpeqb` | Works | `k_avx` |
| VEX `vpcmpeqb` with an unaligned memory operand | Works | `p_vex_unaligned` |

VEX is a newer encoding that can name three registers. The VEX forms that work are the 128-bit forms of SSE2 operations. The cells use only SSE2. The site's processor is plain `qemu64`. The Reference says that SSE2 and SSE3 are available and that anything newer is not guaranteed. It bans `syscall`, `sysenter`, `int`, `int3`, `ud2`, `in`, `out` and `rdrand`. `rdtsc` works and returns the tick.

Probe `s_vex_src` showed that a VEX compare reads its destination, not its first source. Unicorn has the same bug. `cells/vex_emu.py` runs that instruction the way the site does. Woe, Conceit and Endemic are VEX variants of Scourge, Covetous and Contagion. They are broken on the site and must not be submitted.

Legacy SSE instructions that read memory need an address that is a multiple of 16, so each constant has `align 16`. The view window can start at any byte, so the cells load it with `movdqu`.

The cells use no loops and no stack, and they do not write to memory. Scourge and Complacency do not touch the cell memory. Contagion uses it only on its scout path. These are project speed rules, not game rules: the Reference allows mutable data in the cell memory (`[rdx]`) or on the stack, and the Quick start says "The stack is yours." The hazards that the Reference names are writes to the code or view pages and running off the stack.

Each cell is written by `cells/gen_<name>.py`, which builds both the assembly and the tables. See [cells-and-experiments.md](cells-and-experiments.md).

## How the cells were checked

`cells/check_cells.py` runs NASM, static checks, and, with Unicorn, a comparison with the Python reference ([cells-and-experiments.md](cells-and-experiments.md) has the details). Complacency was compared on 200,512 cases with no mismatches.

Passing the checker does not show that a cell works on the site, so the last check is the Sandbox: up to three opponents, 16 by 16, 500 ticks. Each match page shows the average and maximum instructions per call and a fault log. Complacency's two Sandbox games had no faults, with an average of 39 instructions per call and a maximum of 53. The simulator is a separate, approximate check: [simulator.md](simulator.md).

## Contagion additions

Contagion is Scourge with a feeding floor of 12 and two additions:

- **Grab assist.** A donor with no empty neighbour and 8 or more energy feeds a poor friend with 4 or less, when that friend has room to grow and no enemy is in view.
- **Scouts.** A start cell within 10 squares of an edge splits a scout child. A scout moves along its bearing at most 10 times, and stores its origin and steps in the cell memory.

## Open items

- The refill path is 11 instructions. The only 10-instruction version uses the VEX form, which is broken on the site.
- The next cell to build is Schism: `designs.md` 10.4.

## Glossary

| Term | Plain meaning |
|---|---|
| Action byte | The one-byte answer a cell returns in `al`. It says what the cell does, such as rest, bite or split. |
| Branch or jump | An instruction that moves the processor to another place in the code. A jump is taken when it moves. |
| Constant | A fixed value stored in the cell file, such as `kEnemy`. |
| Emulator | A program that runs machine code in software. Unicorn is the emulator that the checker uses. |
| Flag | A single bit that the processor sets after some instructions. The zero flag is set when the result is zero. |
| Instruction | One step the processor performs, such as copy, compare or jump. |
| Instruction count | The number of instructions a cell runs in one turn. |
| Lane | One byte position inside a 16-byte register. |
| Lookup table | A list in memory. The cell reads one entry from it, using an index, to get the answer. |
| Mask | A number whose bits each answer one yes-or-no question, such as whether a square has an enemy. |
| NASM | The assembler that turns the cell's source text into machine code. |
| Register | A small storage slot inside the processor. The cell's register names include `rax`, `ecx` and `xmm0`. |
| Return address | The place in the game that a cell's call returns to. A `ret` goes there. |
| SIMD | Single instruction, multiple data. One instruction works on several values at once. |
| SSE and SSE2 | SSE is a family of SIMD instructions for 128-bit registers. SSE2 is its second set, which the cells use. |
| Taken jump | A jump that actually moves the processor. It counts as an instruction. |
| VEX | A newer way to encode SSE-style instructions. It can name three registers. The site runs the VEX compare with the wrong source, so the cells do not use it. |
| View | The cell's 5 by 5 block of squares, which the game passes in memory. |
| Window | A 16-byte slice of the view, read into one register. |
