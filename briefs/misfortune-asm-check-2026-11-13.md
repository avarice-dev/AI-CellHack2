# Misfortune asm check (cap B, exact 1), 2026-11-13

For the reviewer: section h of `briefs/misfortune-build-review-2026-11-13.md`, run on the final asm. Nothing is uploaded. No site request was made.

Files:

- `cells/misfortune.asm`: the cell (generated; do not edit by hand).
- `cells/gen_misfortune.py`: the generator. It builds on `gen_bane2.generate()`, as Conviction does.
- `cells/check_cells.py`: new branch `misfortune` (`check_misfortune`, `misfortune_path_table`, `diff_misfortune`). `Runner.call` has a new option, `reset_all`. It zeroes rbp, r9 to r15 and xmm0 to xmm15 before the call, as the site does (probes calib-q and calib-r, `data/site-observations-2026-11-08.md`).
- Outputs (git-ignored): `sim/out/misfortune/asm/check_cells.txt`, `unicorn-diff.txt`, `path-table.md`, `mutations.txt`.

Reference: `make_misfortune(cap='B', exact=1)` in `sim/cells_ref.py` (commit 6de02f6). The asm has no cap A or cap N code.

## 1. Result

| Check | Result |
|---|---|
| check_cells | `python3 cells/check_cells.py --only misfortune`: ALL CHECKS PASSED, exit 0 (`sim/out/misfortune/asm/check_cells.txt`). The other cells were not re-run. |
| Unicorn diff (action, count, memory 0-63) | 59,058 cases, 0 mismatches |
| Path table (section b, B1 column) | 21 of 21 rows equal (action and count) |
| esi on every energy-indexed access | 3 operands, all with the 0x67 prefix; no rsi-indexed memory operand |
| Table bytes | equal to the generator (11 tables) |
| SSE constants used by `pcmpeqb` | 16-byte aligned (11) |
| Size | source 42,539 bytes (limit 64 KB); binary 23,658 bytes (limit 32 KB) |

## 2. Listing

Entry assumptions: rax = 0, xmm0 = 0, esi = own energy. The site zeroes rax, the other general registers and xmm0 to xmm15 before every call (calib-q, calib-r).

```
start:
 1  or      al, [esi + CELLMEM_BASE + 13]          ; armed bite: slot(e)
 2  jnz     EXIT_ADDR                              ; = 2
 3  movzx   ecx, byte [abs CELLMEM_BASE + 8]       ; e0
 4  movdqu  [rcx + CELLMEM_BASE + 9], xmm0         ; zero slots e0-4 .. e0+11
 5  movdqu  xmm0, [rdi + VIEW_CELLS + VIEW_UP]     ; Bane v2.2 scan, unchanged
 6  pcmpeqb xmm0, [kEnemy]
 7  pmovmskb ecx, xmm0                             ; ecx is written again here
 8  or      al, [abs bite_tbl + rcx]
 9  jnz     arm                                    ; not taken: Bane v2.2's paths (core + 4)
arm:
10  mov     [abs CELLMEM_BASE + 8], sil            ; e0
11  movzx   edx, byte [abs dir_tbl - ACT_EAT + rax] ; view offset of the target's energy
12  movzx   edx, byte [rdi + rdx]                  ; te
13  lea     edx, [rax + rdx*4 - ACT_EAT]           ; te * 4 + d
14  movzx   edx, byte [abs row_tbl + rdx]          ; d * 6 + k
15  shl     edx, 4
16  movdqu  xmm1, [abs pat1_tbl + rdx]
17  movdqu  [esi + CELLMEM_BASE + 9], xmm1         ; slots e0-4 .. e0+11
18  mov     byte [abs CELLMEM_BASE + 63], 0        ; slot 50 never armed
19  ret                                            ; = 19
```

The cap B rule is at `boxed:`, ahead of Bane's boxed block. It has no branches before its exit test:

- Two windows of the view (indices 0-15 and 9-24) are compared with constants that match only on the ring squares 6, 8, 10, 14 and 16, 18, 22. The result gives enemy lanes and empty lanes. Square 2 comes in through a word table (`c2e_tbl`, `c2z_tbl`) as lane 15.
- `ring_e` and `ring_z` map the 10 lane bits 6-15 to a byte. `en_up` to `en_left` map the four edge energies. `e6_tbl` is indexed by esi.
- `idx = ring_e & ring_z & (en_U | en_R | en_D | en_L) & e6`. The hold edges are in bits 0-3, and the lift edges are in bits 4-7. `cap_tbl[idx]` is the action: the first hold edge (UP, RIGHT, DOWN, LEFT), else the first lift edge.
- On the boxed path an edge square is a friend or a wall, and a wall has energy 0 (`docs/cellhack.inc`). So the energy test (47 or 48 and more) also stands in for the friend test.

The test is 31 instructions, up to and including `jnz cap_hit`. Filler instructions (`xor r11d, r11d`) set the counts to the reference's counts:

- a hit is 17 + 31 + 31 filler + `ret` = 80;
- a miss is 31 + 25 filler = 56, which is 4 x 6 + 4 x 8.

Without the filler, a miss would cost 31 and a hit 49. The reference's 6 and 8 per edge were estimates (build review, j.3). If the reviewer prefers the shorter counts, both the reference and `CAP_MISS_N` / `PULL_N` in the generator must change together.

## 3. Unicorn diff

`diff_misfortune` (seed 20261113) compares the action, the instruction count (every executed instruction, as the site counts) and memory bytes 0-63 after the call:

- energies 0-50, 400 views per energy, in four kinds: bite (an enemy beside the cell), boxed, open (an empty neighbour, no enemy beside), any. Random 64-byte memory: slot(e) is zero in 75% of the cases, so the slow paths run. Byte 8 is 0-50 in 90% of the cases, else 0-255. Byte 1 and bytes 4-7 vary, so the walker paths run. Empty and wall squares have energy 0. Friend and enemy energies lean to the cap.
- after every arming, one chain call on the memory that the arming left, at an energy from e0 - 4 to e0 + 11;
- a boxed sweep: every empty / friend / enemy pattern of the 8 ring squares (3^8 = 6561) x 5 edge-energy patterns (walls included), with my energy 5, 6, 30, 47 or 50.

Result: 59,058 cases, 0 mismatches (`sim/out/misfortune/asm/unicorn-diff.txt`, with the cases per path and count). The longest counts seen: armed 2, arming 19, cap rule 80, open paths 68, boxed paths 141 (random) and 143 (sweep). The reference gives the same count in every case.

**Shown failing first** (`sim/out/misfortune/asm/mutations.txt`, 60 views per energy plus the sweep, 36,746 cases each). Each mutant of the generator is caught:

| Mutant | Mismatches |
|---|---|
| none (control) | 0 |
| prefix store removed | 2540 |
| pattern store at 10 + e0 (off by one) | 1071 |
| slot 50 not cleared | 733 |
| hold at 47 | 7430 |
| lift at 48 | 3414 |
| feed floor 5 | 1390 |
| k at most 4 | 576 |
| miss padded to 55 | 11120 |
| hit padded to 79 | 22469 |
| ring lanes of squares 2 and 22 swapped | 4219 |
| square 2 not read | 2543 |
| rsi in the armed bite (static check) | flagged: "rsi-indexed memory operand" |

## 4. Section h items

**esi on every energy-indexed access.** The checker reads the NASM listing. It finds every memory operand that contains esi and checks that its bytes start with 0x67:

```
or   al, [esi + CELLMEM_BASE + 13]      ; armed bite
movdqu [esi + CELLMEM_BASE + 9], xmm1   ; pattern store
and  r10b, [esi + e6_tbl]               ; cap B: lift needs my energy >= 6
```

No memory operand uses rsi. Bane's `lea r9d, [rsi - 4]` is arithmetic, not a memory access, and its 32-bit result does not depend on the upper bits. `cmp sil, [thr_tbl + rcx]` and `cmp esi, n` do not index memory by energy.

**Entry assumptions.** rax = 0: the armed bite returns the slot byte in al, and `arm` uses rax as `ACT_EAT + d` (only al was written). xmm0 = 0: the prefix stores xmm0. After the prefix, ecx is not read before the scan writes it again (`pmovmskb ecx, xmm0`, instruction 7). Instructions 3-7 have no branch, so every slow path starts with the new ecx.

**Tables** (addresses from `cells/build/misfortune.map`):

| Table | Address | Contents |
|---|---|---|
| `pat1_tbl` | 0x100928 | 24 rows of 16 bytes, row d * 6 + k. Byte j is slot e0 - 4 + j. Row (d, k) holds EAT + d (0x30 + d) at j = 0, 2, ..., 4 + 2k and 0 elsewhere. Row k = 0 is all zero. Example (RIGHT, 5): `31 00 31 00 31 00 31 00 31 00 31 00 31 00 31 00`. |
| `row_tbl` | 0x100528 | 1024 bytes, index te * 4 + d (te 0-255): d * 6 + min(5, max(0, ((te & 63) + 1) // 2 - 1)). |
| `dir_tbl` | 0x100524 | 71, 77, 81, 75: view offset of the energy of the neighbour UP, RIGHT, DOWN, LEFT. |
| `cap_tbl` | 0x101BA8 | 256 bytes: the hold / lift action by idx. |
| `a50_tbl`, `pat0_tbl` | none | cap A and exact 0 only; not built. |

**Byte 63 (slot 50).** The arming path always stores 0 to byte 63 after the pattern store, so slot 50 is never armed (cap B). A cell at energy 50 reads byte 63, finds 0, and takes a slow path. The prefix also zeroes byte 63 when the stored e0 is 39 to 50. The diff checks byte 63 in every case, and the "slot 50 not cleared" mutant is caught.

## 5. Site facts still unverified

1. **Stores past byte 63.** The pattern store writes bytes 9 + e0 to 24 + e0, so it reaches past byte 63 for e0 >= 40. The prefix does the same for a stored e0 >= 40, up to byte 74 at e0 = 50. `docs/cellhack.inc` maps 4 KB of cell memory, read and write (CELLMEM_SIZE), and keeps only the first 64 bytes (MEM_SIZE). So the stores should land in scratch, but no site probe has shown it. If such a store faults, the cell loses its action on that tick.
2. **Per-call instruction limit.** `docs/cellhack.inc` gives INSN_BUDGET = 1000. Cap B's boxed paths reach 140 in the path table (boxed interior, all friends at 50), and the diff saw at most 143 (a boxed sweep case). Our own cells have run at most 91 on the site (Bane v2.2 match pages); Bane v2.3a's longest path is 85. Rivals' match pages show maxima of 202-203 instructions per call, so the site runs calls that long. A path above 91 has not yet run in one of our cells on the site.
3. **Byte 8 and the slots at the first call.** The first cell's memory is assumed zero (then e0 = 0 and the prefix clears bytes 9-24). This is not a new assumption; Bane v2.2 relies on it too.

Sandbox checks for 1 and 2: a sandbox game with fault counts and the match page's maximum instructions per call.

## 6. Known limitations (logged in issues.md, left as built)

- k = 0 arming at exact 1: a cell that is stunned on its arming tick by a weak enemy (te <= 2) is not armed on the next tick.
- Blind runs are unbounded: with 2 or more enemies on edges the energy stays level and the same slot is read again, so friends get bitten. The measured cost is about 3.5% of the energy taken from enemies.

## 7. Notes for the reviewer

- The third return value of the reference (the count without taken jumps) is not compared, because Unicorn counts every instruction, as the site does. The asm's cap block has no taken jump on a miss. The reference counts 8 there (one per edge). This changes only `order_by_alt`, which is off by default.
- The comment at the top of the Misfortune section in `sim/cells_ref.py` still shows `rsi` in the entry line. It is a comment in a signed-off file, so it was left unchanged.
