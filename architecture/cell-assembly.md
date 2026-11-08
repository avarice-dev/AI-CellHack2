# Cell assembly: the instructions and the reasons for them

This document explains the x86-64 assembly code inside the CellHack2 cells. It covers which instructions the cells use, why those instructions were chosen, and how each decision is written in code. You do not need to know assembly to read it. Each instruction is explained the first time it appears, and the [glossary](#glossary) at the end defines the other terms. The game rules are in [overview.md](overview.md). The history of each cell is in [cells-and-experiments.md](cells-and-experiments.md).

## The short version

A cell gets one turn in each tick. In that turn it returns one action, such as bite, split, feed or rest. Speed is the main design goal. A cell that runs fewer instructions acts earlier in the tick. An earlier turn can win a square that a rival also wants.

To keep the turn short, the cells use a method that the project calls a one-step lookup. The cell copies its 5 by 5 view into a 16-byte register. It compares all 16 bytes with one instruction and packs the result into a single number, called a mask. It then uses that number as an index into a table that holds the answer. The decision costs one memory read. It does not cost a long chain of if-statements that each test one case.

The cells also use only a small set of instructions. The site accepts some instruction sets and rejects others, so the project tested each set before using it.

## The rules in brief

Each cell sees the 5 by 5 block of squares around it, including its own square. It can bite an adjacent enemy, split into an empty neighbour, feed a friend or rest. A split or a feed needs enough energy. A cell at the energy cap of 50 gains nothing from resting. The full rules are in [overview.md](overview.md).

## Why instruction count matters

Within a tick, the game runs the cells in order of instruction count. A cell with a lower count plays first. The count includes every instruction that the cell runs in its turn. It also includes each jump that is taken, and the final `ret`. A `ret` is the instruction that ends the call and hands the action back to the game. All colonies share one pass per tick. Cells with equal counts are put in a random order, and that randomness comes only from the match seed. A match with the same seed therefore replays identically (Rules, pages 2 and 3).

The game documents state this rule. The Reference says: "The engine counts every instruction." The Quick start counts `mov al, ACT_REST` and `ret` as two instructions. The site agrees. A probe cell that ran a `mov` and a `ret` averaged 2 instructions per call. The `b_jmp` probe, written to test taken jumps, was not needed after this.

The game also caps a call at 1000 instructions (`INSN_BUDGET` in `docs/cellhack.inc`). A call over the cap is a fault, and the cell does nothing that tick. The longest path in Covetous is 60 instructions, and the longest feed path in Scourge is 53. The cap does not limit these cells.

Why do a few instructions matter so much? The Rules say that a square freed by a death cannot be entered until the next tick. (A square freed by a move can be entered later in the same tick, and two cells cannot swap places.) The replays agree. The race for a freed square is therefore decided by turn order in the next tick, which means by instruction count. A cell that acts first takes the square.

The total instruction count also matters at the end of a match. Living colonies are ranked by population, then by total energy, then by fewer instructions in total, then by the lower colony number (Rules, page 2).

## The core trick: one compare, one lookup

A register is a small storage slot inside the processor. Instructions read and write registers much faster than they read memory. The cells use general registers such as `rax`, and 16-byte registers named `xmm0` to `xmm15`. The 16-byte registers belong to SSE, a family of instructions that work on several values in one step. SSE is explained in the [glossary](#glossary).

The game passes the cell a pointer to its view in the `rdi` register. The view holds 25 bytes, one for each square of the 5 by 5 block, in row order. The cell itself sits at index 12. Index 7 is the square above, index 11 is the square to the left, index 13 is the square to the right and index 17 is the square below. Here is the start of the bite code from `cells/covetous.asm`, which is the bite that every later cell reuses:

```nasm
start:
	movdqu		xmm0, [rdi + VIEW_CELLS + VIEW_UP]	; view idx 7..22
	pcmpeqb		xmm0, [kEnemy]
	pmovmskb	ecx, xmm0			; bits 0 UP, 4 LEFT, 6 RIGHT, 10 DOWN
	or		al, [abs bite_tbl + rcx]	; rax = 0 at entry: al = eat action, ZF = no enemy
	jnz		EXIT_ADDR			; bite: leave through the return address
```

The first four lines do the core trick, and each step is one instruction:

1. `movdqu` copies 16 bytes from the view into `xmm0`. The `u` stands for unaligned. The copy works at any address, so the window does not have to start on a multiple of 16.
2. `pcmpeqb` compares two sets of 16 bytes, one byte at a time. Where two bytes are equal, it writes 0xFF, which has all eight bits set. Where they differ, it writes 0. The constant `kEnemy` holds the enemy value, which is 2, in the four neighbour positions. In every other position it holds 0xFF. No square in the view has that value, so those positions never match.
3. `pmovmskb` reads the top bit of each of the 16 bytes and packs the 16 bits into one number, `ecx`. A matching byte has its top bit set, so each adjacent enemy becomes a single 1 bit. The result is the mask. Bit 0 means UP, bit 4 means LEFT, bit 6 means RIGHT and bit 10 means DOWN.
4. `or al, [abs bite_tbl + rcx]` reads the table entry that the mask points to, and combines it with `al`. The `abs` keyword means the table's address is fixed when the file is built. The mask in `rcx` is added to that address.

A worked example shows how the table gives the answer. Mask 0x411 has bits 0, 4 and 10 set. That means enemies stand UP, LEFT and DOWN, and RIGHT is free. The rule for three enemies is to bite the side opposite the free side, which is LEFT. The table entry for 0x411 is 0x33. The value 0x30 means bite, and 3 means LEFT. So the cell bites LEFT.

The bite table has 1106 entries, one for each mask value from 0 up to 0x451. Only the four neighbour bits can ever be set, so most entries are zero. The generator script fills every entry. A person does not type the table by hand.

A chain of if-statements would test one case after another. Each test costs at least one compare and one jump. The table costs one read, whichever squares hold enemies. This is why the project calls the method a lookup.

## The five-instruction bite

The bite is the first thing every cell checks. Its five instructions are the five lines shown above. The first three build the mask. The fourth reads the answer. The fifth leaves the cell if there was a bite.

The fourth line does two jobs at once. The table byte is the action. The `or` instruction also sets the zero flag, which is one bit that the processor keeps. The zero flag says whether the last result was zero. A mask with no adjacent enemy points to a zero table byte. The zero flag is then set, and the fifth line does not jump. The cell goes on to the code below the bite, which is called the slow path. The design notes say that a miss costs the same 5 instructions as a hit.

The fifth line, `jnz`, means "jump if not zero". It jumps when the zero flag is clear, which means there is an enemy. The jump goes to `EXIT_ADDR`, which is the address that a `ret` would return to. The call ends at that address. The `ret` instruction is skipped, so the bite saves one instruction. This is why the Covetous header counts the bite as 5 instructions with taken jumps, and 4 without them.

The design notes call this bite F5. It is 5 instructions in every direction and uses no memory. The notes compare it with the rivals. The replay study found that the strongest rival bots bite in about 4 instructions in one fixed direction. They bite in about 6 in a second direction, and in 8 or more in the other directions. The 5-instruction bite beats every rival's second direction and every slower side. It loses only to a rival's single 4-instruction direction. Covetous tested this idea on the ladder. Its first check gave 60.4% wins in 217 games.

Four facts make the trick safe to use:

- The `or` only gives the right answer if the rest of `al` is zero when the call starts. Probe `c_rax_probe` ran on the site. It found that `rax` was zero on every call, with no faults.
- The bite does not read the registers that the game might leave with old values. Probe `r_gpr_zero` found that `rbx`, `rcx`, `rbp` and `r8` to `r15` are zero at entry. Probe `q_xmm_zero` found that `xmm0` to `xmm15` are zero. The bite overwrites `xmm0` and `ecx` before it reads them, so the result does not depend on either probe. The probes still show that the site starts each call in a known state.
- The `jnz` exit depends on the site treating a jump to the return address like a `ret`. Probe `e_jexit` ran `mov al, ACT_REST` followed by `jmp EXIT_ADDR`. On match 99887 against a bot called Idle, it used 2 instructions per call, had no faults and grew the colony to 50 energy.
- The jump leaves the stack pointer 8 bytes lower than a `ret` would. The game resets the stack before every call, so this does no harm. The Covetous generator notes this.

## Splitting, and the energy threshold

A split creates a child on an empty neighbouring square. The split code reuses the same pattern as the bite. It compares the view with a constant, this time one that marks empty squares with 0:

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

The `test` instruction checks whether the mask is zero, and sets the zero flag to say so. The `jz` instruction jumps to the feeding code when no neighbour is empty. Otherwise the table entry gives the split direction, and `ret` returns it to the game.

Before the split code runs, the cell must have enough energy. The threshold depends on the situation. The 5x5 check that decides this is the most complicated part of the early code:

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

The `esi` register holds the cell's energy. The `cmp` and `jb` pair means "compare, and jump if below". So a cell below 5 energy rests. The 25 squares of the 5x5 view do not fit in one 16-byte window. The cell therefore uses two overlapping windows, and `por` joins their results. The constants keep the cell's own square out of the result, so the cell does not count itself as an enemy.

The threshold has three values, and each one has a reason:

- The threshold is 5 in ordinary play. The game sets 5 as the least energy that allows a split (`SPLIT_MIN` in `docs/cellhack.inc`).
- The threshold is 16 while an enemy is anywhere in the 5x5 view. A split at 16 gives the child 8 energy. The design notes call this the prey rule: with an enemy near, a split is worth making only if the child gets at least 8.
- From tick 2980 on, the threshold is 5 again. The design notes set an endgame rule that fills every empty neighbour from tick 2980. The notes do not say how the exact tick was chosen.

## Feeding from full cells

Feeding gives 2 of the feeder's energy to the cell in the chosen direction. A feeder with less than 2 gives all it has, and dies if that was all of it. The target can be a friend or an enemy (Rules, page 2), so the cells check for a friend first. A fed cell that also rests gains 3 in that tick: 2 from the feed and 1 from its own rest. There is no feed bonus. The reason for feeding is simple. A cell near the cap of 50 gains little from resting, so it can give energy away with little cost. The Covetous rule is that a cell at 47 energy or more feeds when it would otherwise rest. It feeds its poorest friend neighbour, but only if that friend has 46 energy or less:

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

The `r8d` register keeps the lowest friend energy found so far. It starts at 255, which is higher than any real energy, so the first friend always wins. The block repeats for the right, down and left neighbours. Each repeat checks whether the square is a friend. If it is, the cell reads its energy and keeps it if it is the new lowest. The `ACT_FEED + DIR_UP` value is the action byte for "feed the square above".

The design notes give two reasons for the 47 and 46 limits. A target at 47 or more is close to the cap, so feeding it gains little. The replay study also found that one rival, Aegis, wasted 34% of its feeds on full cells. Scourge uses a different feeding floor of 16 energy, and Contagion uses 12. The design notes plan an experiment, E2, to compare floors of 8, 12, 16 and 20. The sources read for this document record no results for E2.

## The refill gate in Scourge

A freed front square is an empty square next to the cell, where an enemy could reach the square next tick. The design notes say that a freed square is one with an enemy in the square beyond it or beside it. Scourge's bet is that kills can turn into land, so it tries to retake these squares quickly. It checks for them right after the bite fails:

```nasm
slow:						; 5 instructions so far
	movdqu		xmm1, [rdi + VIEW_CELLS + 6]	; view idx 6..21
	pcmpeqb		xmm1, [kRefill]			; empty neighbours, enemies beside/beyond them
	pmovmskb	ecx, xmm1			; mask 0..7607
	mov		al, [abs act_tbl + rcx]		; split to take (0 = no empty neighbour)
	cmp		sil, [abs thr_tbl + rcx]	; energy it needs (12 refill, 16 other, 255 boxed)
	jae		EXIT_ADDR			; refill / split: 11 instructions
```

The window starts at view index 6, which is one of the squares that the refill check needs. The constant `kRefill` marks the four neighbours as empty and six more squares as enemies. Those six squares are the diagonals and the squares two steps away, to the left and right. The mask now combines two questions. The first is which neighbours are empty. The second is whether an enemy stands beside or beyond each one. The mask can reach 7607, so the lookup table has 7,608 entries.

Two tables answer the question. `act_tbl` gives the split direction for the mask. `thr_tbl` gives the energy that split needs. A refill needs 12 energy. A normal split needs 16. A boxed cell, which has no empty neighbour, needs 255, so it can never split. The `cmp sil, [...]` line compares the cell's energy with that number. The `jae` instruction then leaves through the return address when the energy is enough.

The count is 11 instructions: the 5 bite instructions, plus the 6 lines above. The design notes gave the refill path a target of 10 or fewer. The built path is 11, and the header records that figure. The 10-instruction version exists only in the VEX variants, Woe and Endemic, which are broken on the site.

Why 12 energy? A split halves the energy between parent and child. A parent with 12 energy gives its child 6. The design notes set this child size, because AtomPush's children were 5 to 7 energy in the replay study. A child at least that big is worth the cost.

Why does the window stop short of squares 2 and 22? These are the squares beyond UP and DOWN. The window would need 21 bytes to hold indexes 2 to 22, and a single 16-byte window is too small. Reading them would take at least 3 more instructions on the path that has to stay fast. The design notes chose to leave them out.

The ladder study recorded that Scourge refilled 98% of the squares that its rivals ate from it. Scourge's ladder rating was 1511 after 589 games, which is the last check before it was retired.

## The prey hold, and why Complacency drops it

The prey hold is a rule that Covetous and Scourge both use. With 5 to 15 energy, and an enemy anywhere in the 5x5 view, the cell rests instead of splitting. The rule lasts until tick 2980. This is the Scourge version of the code:

```nasm
threat:
	cmp		dword [rdi + VIEW_TICK], 2980
	jae		EXIT_ADDR			; late: split anyway
rest:
	mov		al, ACT_REST
	ret
```

The prey rule asks that a split near an enemy leave the child with at least 8 energy. A split at 5 to 15 energy would leave a child of 7 or less, so the cell waits instead. The project then asked whether this hold slowed Scourge's early growth. The replay study found that Scourge lost the land grab. The winners were ahead from about tick 21 onward. At tick 200, Scourge had about 800 cells on the real ladder, and the winners had about 2400. The design notes name the prey hold as the suspected cause. This is a suspicion, not a measured result.

Complacency tests that suspicion. It is Scourge with the hold removed. Its middle split is a plain split at 5 energy or more, with no 5x5 check. That middle split path costs 16 instructions. The design notes compare this with Scourge's 24 to 27 instructions on the same paths:

```nasm
	cmp		esi, 5
	jb		rest
	ret					; split: no prey hold
rest:
	mov		al, ACT_REST
	ret
```

The design notes tested four choices for when the hold should stop: at tick 200, 300, 500, or never. They also tested a version that held only for an enemy on a diagonal. In the sweep, "never" gave the highest final population in all three mixes. Every choice gave the same win rate. The diagonal version was worse than every tick choice, so it was not built. The project chose "never" for these reasons. It gives the most land in the simulator, and it is the simplest code.

The simulator results have limits, and the design notes say so. In a head-to-head mix on seeds 9 to 16, Scourge scored 2.50 points and Complacency scored 1.75. A mirror run, with the two cells swapped, showed that the head-to-head winner followed the start position, not the cell. The design notes conclude that the head-to-head numbers reflect start luck. What held in the simulator was more land for Complacency and the same win rates. The notes also say the simulator does not reproduce Scourge's real land-grab deficit. So it cannot show how much of that deficit the hold causes.

Complacency was tested on the site. Its first Sandbox games placed first with 88 cells, where Scourge had 82, and second with 94 cells, where Scourge had 162. Both ran with no faults. On 2026-11-08 the owner approved it for the ladder. At its first check, it had a rating of 1510 after 69 games and 66.7% wins. Scourge had 1511 and 67.6% wins at the same check. The design notes ask for at least 50 games before a cell is judged. Complacency had 69 games at that check. The project's open items still call for more games before it is compared with Scourge's last rating.

## Constraints and what was ruled out

The site runs a limited set of instructions. Probe cells in `cells/calib/` tested each instruction set. The results are these:

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

The VEX prefix marks a newer encoding of an instruction, which can name three registers, not two. The VEX forms that work are the 128-bit forms of SSE2 operations. The site rejects the forms of the SSSE3 and SSE4 instructions. The cells use only SSE2 in their final form. The site's processor model is the plain `qemu64` model. The Reference says that SSE2 and SSE3 are available and that anything newer is not guaranteed. The Reference also bans `syscall`, `sysenter`, `int`, `int3`, `ud2`, `in`, `out` and `rdrand`. The instruction `rdtsc` works and returns the tick number.

The VEX forms have a more serious problem. Probe `s_vex_src` tested whether a VEX compare reads its first source register or its destination. It gave a bad-action fault on every call, so the site uses the destination. The local emulator, Unicorn, has the same bug. The project wrote `cells/vex_emu.py` to run that one instruction the way the site does. Woe, Conceit and Endemic are VEX variants of Scourge, Covetous and Contagion. They use the newer form to cut one or more instructions. Woe died in two Sandbox games, with peaks of 4 and 5 cells while Scourge grew. The design notes mark all three as broken on the site and not to be submitted. Their simulator figures assumed the three-operand form, so those figures do not describe the site.

Legacy SSE instructions that read memory need the address to be a multiple of 16. The file places each constant on a 16-byte boundary, with `align 16`. The view window can start at any byte, so the cells load it with `movdqu`, which has no such rule. The VEX forms do not have the alignment rule, but they are the broken forms described above.

The cells follow three more rules. They do not write to memory. The Scourge and Complacency headers say that they do not read or write the cell memory. Contagion uses the cell memory only on its scout path. The cells also use no loops and no stack. These are the project's own speed rules, not game rules. The game allows both: the Reference says to keep mutable data in the cell memory (`[rdx]`) or on the stack, and the Quick start says "The stack is yours." The project avoids them because each extra instruction makes the cell act later in the tick and adds to the total that breaks end-of-match ties. The real hazards that the Reference names are writes to the code or view pages and running off the stack, which are memory faults.

The cells are generated by Python scripts, not written by hand. The generator for each cell, `cells/gen_<name>.py`, writes both the assembly and the tables. The tables are too large to write by hand. The bite table alone has 1106 entries. The sources give one reason for the approach. A change to a rule is made once, in the script. The tests also import the table functions and check them against the Python reference.

## How the cells were checked

The checker is `cells/check_cells.py`. It runs in a Linux shell, which is WSL on Windows, from the repository root. It needs NASM, the assembler that turns the source into machine code. The Unicorn emulator is optional. Without it, only the static checks run. The checker does four things.

- It runs static checks. NASM must assemble the source. The source must be under 64 KB. The file may not contain forbidden directives. Every instruction must be on the allowed list. Every table entry must point to a valid label.
- It runs an emulator comparison. Unicorn runs the cell and the Python reference on the same inputs, and the results must match. An emulator is a program that runs machine code in software. For Sprint, the inputs covered every combination of the four neighbour types, six energy values, an enemy two squares away or not, and two tick values. Complacency was compared on 200,512 cases with no mismatches.
- It reports the instruction count of each probe, when Unicorn is installed.
- It ends with `ALL CHECKS PASSED`, or with a count of problems.

The allowed list matters. Unicorn runs instructions that the site rejects, such as `popcnt`. The checker therefore rejects those instructions in any cell. Passing the checker does not show that a cell works on the site, so the last check is the Sandbox. The Sandbox runs a saved cell against up to three opponents on a 16 by 16 board for 500 ticks. Each match page shows the average and maximum instructions per call, and a log of any faults. Complacency's two Sandbox games reported no faults, with an average of 39 instructions per call and a maximum of 53.

The simulator is a separate check. It models the game rules, but it is approximate. [simulator.md](simulator.md) explains its limits.

## How the cells evolved

Each cell kept the decisions that had worked and changed one main thing. The first ladder cell was Sprint. It bites in 6 instructions in every direction, eats greedily and never feeds. It grabbed land fast, but it lost races for freed squares to the Atom cells, which belong to other players. Against AtomPush it won 0.5% of 27,339 contested races. Its refill children had a median energy of 25, against 6 for the Atom cells. 
Covetous was built to test one idea: a faster bite is enough. It replaced Sprint's 6-instruction bite with the 5-instruction F5 bite. It fed only from cells near the cap. At the first check it won 60.4% of 217 games. It was later taken off the ladder and replaced by Complacency.

Scourge kept the Covetous bite and its hold rule. It added the refill gate, which retakes freed squares, and feeding from 16 energy. Its bet was that kills can turn into land. It won 74 of its newest 100 games. Most of its losses were settled by the early land grab, between about tick 100 and tick 200. The write-up names the prey hold as the likely cause of the slow grab, but that is a suspicion. The owner took Scourge off the ladder on 2026-11-08 to free a slot. It is still saved on the site.

Contagion kept Scourge's core and added a grab assist. A donor with no empty neighbour and 8 or more energy feeds a poor friend with 4 or less, when that friend has room to grow and no enemy is in view. It also added scouts, which are cells near an edge that move in a straight line from their start. It fed from 12 energy. Contagion won 70 of 95 games, which is 74%. It grew faster early than Scourge, but it fell behind once contact with rivals began, between about tick 75 and tick 200. Its scouts moved only about 6 times per replay, so they were barely used.

Complacency removed the prey hold from Scourge, as described above. It keeps Scourge's bite, refill gate and feeding. On 2026-11-08 the owner approved it for the ladder.

Woe, Conceit and Endemic were the VEX side branch. They are not on the ladder, and the sources read do not record a fix for the site's VEX bug.

## Open items

- The refill path is 11 instructions. The design target was 10 or fewer. The only 10-instruction version uses the VEX form, which is broken on the site.
- The sources read for this document record no fix for the VEX cells.
- Complacency's last check was at 69 ladder games. The project's open items still call for more games before it is compared with Scourge's last rating.
- The experiments E1 to E4 in `designs.md` have no recorded results in the sources read.
- Whether dropping the prey hold fixes Scourge's early land grab has not been measured on the site. The simulator cannot settle it.

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
