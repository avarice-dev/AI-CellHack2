# Misfortune v2 asm check, 2026-11-13

Asm paused by the main session (growth rules may change); this is the check of the built version (commit 44e50da, local only, nothing uploaded).

- `python3 cells/check_cells.py --only misfortune2` (WSL): ALL CHECKS PASSED. Full output: `data/shared-2026-11-13/2026-11-13_asm-check_misfortune2_check_cells.txt` (local-only data folder).
- Unicorn diff against `make_misfortune2()`: 63,916 cases, 0 mismatches (action, instruction count, memory bytes 0-63; registers and xmm zeroed at entry; includes a chain call after every arming and a sweep of stored direction x square occupant x energy x enemy).
- esi-indexed memory operands: 3, all with the 0x67 prefix; rsi-indexed memory operands: 0.
- Size: source 52,995 bytes (limit 64 KB); binary 26,826 bytes (limit 32 KB).
- Planted mutations, all caught (Unicorn diff on 42k cases): refill energy 12 -> 11 (36 mismatches); refill jb -> jbe (37); byte 2 not cleared on fire (1,460); square test jnz -> jz (7,378); hold split at 9 (54); late tick test jb -> jbe (37); late split keeps steps (35); clear path without xor eax (Unicorn fault); clear path forgets mov [2],0 (4,090); word stored at [4] (2,272); wrong view offset in the table (3); cap pad not shortened (22,421).

## Path counts (reference = asm, instructions)

| path | counts (cases) |
|---|---|
| armed | 2 (7042) |
| arm | 22 (2273), 26 (4719), 28 (295) |
| fire | 13 (3684) |
| refill | 23 (2088), 37 (40), 39 (44), 40 (200), 41 (12), 42 (227), 44 (53), 46 (295), 48 (162), 50 (1), 58 (1), 66 (69) |

Required counts met: refill fire 13; armed bite 2; first bite 22 (v1 19; the refill check costs 2, the table dword 1); bite after a stored direction 26 (square taken) / 28 (energy below 12); other slow paths +2; clear without a bite +8 / +10; cap rule 80 when nothing is stored.
Changed from the first reference: first bite 23 -> 22; a bite after a stored direction no longer pays a clear store (26 / 28 instead of 28 / 30 by the old formula); hold split 25 not 24 (+2 on every e < 10 diagonal-hold path); the reference was updated to these counts and `python -m unittest` in sim/ passes.

Site facts still unverified: bytes 64+ of cell memory at entry; the instruction budget per call above the longest path here (145 in the sweep); that a cell may write bytes 2-3 of memory the way v1 left them free (v1 never used them).
