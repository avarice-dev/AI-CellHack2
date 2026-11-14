"""Generate cells/misfortune2.asm (Misfortune v2: v1 + hold='split' at 10 + the checked refill).  No table is written by hand.

    python cells/gen_misfortune2.py     # writes cells/misfortune2.asm next to this file

Built on gen_misfortune.generate() (v1, verified) as gen_bane2 is built on gen_bane.  Reference:
sim/cells_ref.make_misfortune2_ac1() = make_misfortune(cap='B', exact=1, refill='checked', hold='off', hold_min=5,
armed_children=True).  (Until 2026-11-13 this file built V0 = hold 'split' from 10, no armed children; see git history.)
Changes from v1:
 1. hold='off' from 5: an enemy on a diagonal and e >= 5 no longer holds: threat: cmp esi, 5 / jae resume (the dispersal
    logic at `mov ecx, [VIEW_X]`; a walker is not stopped; +2 on that path).  e < 5: steps = 0, rest (the hold's late split
    and its dead tests are gone: e < 5 never splits).
 1b. Armed children.  Every split (gate 1: jae child; the settled / emit path falls into block `child` in place of its ret)
    arrives with al = SPLIT + d.  e & 3 != 1: lea, test, jnz EXIT (3 instructions).  e = 1 mod 4: the 16-byte window
    s - 5 .. s + 10 of the child's square s (cbase_tbl by d) against kEnemy gives the child's four neighbours at lanes
    0 / 4 / 6 / 10 (the lanes bite_tbl is built for; the neighbour toward me is my own friend), bite_tbl gives the child's
    bite (EAT + d', 0 = none: jz EXIT, 10 in all).  Else arm: byte 8 = e // 2 (shr esi, 1), the k = 5 pattern row of d'
    (cpat_tbl) to bytes 9 + c .. 24 + c: 16 in all.  The child's slots lie on even energies; the parent keeps c + 1 (odd).
    Slot 50 (byte 63) is not written.  The child's far neighbour (view idx 2 / 22 for UP / DOWN) is loaded by this window.
 2. Checked refill.  Each bite stores, in one word at memory [2], SPLIT + d (byte 2) and the view offset of that square
    (byte 3, = VIEW_CELLS + view index).  The word comes from the arming table (row4_tbl, a dword: low word = that word,
    high word = the pattern row * 16), so the biting path pays 1 instruction (arm: mov edx, [row4_tbl + rdx*4] /
    mov [2], dx / shr edx, 16 replace movzx / shl).  On every slow path, right after the prefix clean:
        or al, [2] / jz normal                     none stored: +2
        movzx edx, [3] / cmp byte [rdi + rdx], 0   the snapshot square
        jnz clear / cmp esi, 12 / jb clear
        mov byte [2], 0 / ret                      fire: SPLIT + d, 13 instructions in all
    clear (stored, but the square is taken or e < 12): al = 0, then a COPY of the bite scan (a bite goes straight to arm,
    which rewrites byte 2, so no clear store is paid on the biting path); no bite: mov byte [2], 0 / jmp slow.
Counts: first bite 22 (v1 19 + or, jz + 1); bite after a stored dir 26 (square taken) / 28 (e < 12); other slow paths
+2; clear without a bite +8 / +10; cap rule pad 80 when nothing is stored (it is fixed: +5 / +7 after a clear).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sprint as G  # noqa: E402
import gen_bane2 as B2  # noqa: E402
import gen_misfortune as M  # noqa: E402

MEM_ACT = 2                 # byte 2 = SPLIT + d of the last bite (0 = none), byte 3 = view offset of its square
REFILL_MIN = 12             # own energy needed to refill
VIEW_CELLS = 32             # docs/cellhack.inc
FEED_PAD = 6                # Schism feed: min 94 -> 100 instructions, above every armed-child split path (<= 97)
FILL_PAD = M.PULL_N - 2     # fixed pad: pulled cell = 80 when nothing is stored (ex = 2); the reference does the same


def state_word(d):
    return (G.ACT_SPLIT + d) | (VIEW_CELLS + B2.DIR_IDX[d]) << 8


def row4_value(i):
    """te * 4 + d -> dword: low word = the stored word, high word = pattern row * 16 (te 0..255, k from te & 63)."""
    te, d = i >> 2, i & 3
    return state_word(d) | M.row_index(te, d) * 16 << 16


def row4_table():
    vals = [row4_value(i) for i in range(1024)]
    out = ['row4_tbl:\t\t\t; dword by te * 4 + d: low word = SPLIT + d | view offset << 8, high word = pattern row * 16']
    for i in range(0, 1024, 16):
        out.append('\tdd %s' % ','.join('0x%08x' % v for v in vals[i:i + 16]))
    return '\n'.join(out) + '\n'


REFILL = """\
	or		al, [abs CELLMEM_BASE + %(act)d]	; checked refill: SPLIT + d of the last bite (al = 0 here)
	jz		normal				; none stored: +2
	movzx		edx, byte [abs CELLMEM_BASE + %(act1)d]	; view offset of that square (snapshot)
	cmp		byte [rdi + rdx], CELL_EMPTY
	jnz		clear				; taken
	cmp		esi, %(rmin)d
	jb		clear				; too weak
	mov		byte [abs CELLMEM_BASE + %(act)d], 0	; cleared first: a child starts clean
	ret					; refill: 13 instructions
clear:
	xor		eax, eax
	movdqu		xmm0, [rdi + VIEW_CELLS + VIEW_UP]	; copy of the bite scan: a bite rewrites byte 2 in arm
	pcmpeqb		xmm0, [kEnemy]
	pmovmskb	ecx, xmm0
	or		al, [abs bite_tbl + rcx]
	jnz		arm
	mov		byte [abs CELLMEM_BASE + %(act)d], 0
	jmp		slow
normal:
"""

ARM_FROM = ("\tmovzx\t\tedx, byte [abs row_tbl + rdx]\t; d * 6 + k\n"
            "\tshl\t\tedx, 4\n")
ARM_TO = ("\tmov\t\tedx, [abs row4_tbl + rdx*4]\t; low word: the refill word, high word: pattern row * 16\n"
          "\tmov\t\t[abs CELLMEM_BASE + %(act)d], dx\t; SPLIT + d and the square's view offset\n"
          "\tshr\t\tedx, 16\n")
THREAT_BLOCK_FROM = '\nthreat:\n'
THREAT_BLOCK_END = '\nrest:\n'
THREAT_TO = """
threat:
	cmp		esi, %(smin)d
	jae		resume				; hold = 'off': e >= %(smin)d goes on with the dispersal logic
	mov		byte [abs CELLMEM_BASE + %(steps)d], 0	; a walker stops here (e < %(smin)d: rest)
"""
RESUME_FROM = '\tmov\t\tecx, [rdi + VIEW_X]\t\t; x | y << 16\n'
SPLIT_FROM = '\tlea\t\teax, [r9 + ACT_SPLIT]\n\tret\n'
GATE_FROM = '\tjae\t\tEXIT_ADDR\t\t\t; refill / split: 11 instructions\n'
CHILD = """\
child:						; al = SPLIT + d (eax = al), esi = my energy
	lea		edx, [rsi + 3]
	test		dl, 3				; e & 3 == 1: the child gets e // 2 (even), I keep an odd energy
	jnz		EXIT_ADDR			; not armed: 3 instructions
	movzx		edx, byte [abs cbase_tbl - ACT_SPLIT + rax]	; view offset of the window s - 5 (s = the child's square)
	movdqu		xmm0, [rdi + rdx]		; the child's neighbours UP / LEFT / RIGHT / DOWN at lanes 0 / 4 / 6 / 10
	pcmpeqb		xmm0, [kEnemy]
	pmovmskb	ecx, xmm0
	movzx		edx, byte [abs bite_tbl + rcx]	; the child's bite: EAT + d', 0 = no enemy beside the child
	test		edx, edx
	jz		EXIT_ADDR			; no enemy: 10 instructions
	shr		esi, 1				; the child's energy
	mov		[abs CELLMEM_BASE + %(e0)d], sil	; e0 = the child's energy
	shl		edx, 4				; (ACT_EAT + d') * 16
	movdqu		xmm1, [abs cpat_tbl - ACT_EAT * 16 + rdx]	; k = 5 row of d'
	movdqu		[esi + CELLMEM_BASE + 9], xmm1	; slots c - 4 .. c + 11 (even energies hold the bite)
	ret					; armed child: 16 instructions
"""


def cbase_line():
    return ('cbase_tbl:\tdb %s\t; view offset of the window s - 5 for the child UP, RIGHT, DOWN, LEFT\n'
            % ', '.join('%d' % (VIEW_CELLS + i - 5) for i in B2.DIR_IDX))


def cpat_table():
    out = ['\talign 16', "cpat_tbl:\t\t\t; k = 5 pattern row of d' = UP, RIGHT, DOWN, LEFT (bytes 9 + c .. 24 + c)"]
    for d in range(4):
        out.append('\tdb %s\t; d %d' % (', '.join('0x%02x' % x for x in M.pattern_row(d, M.K_MAX)), d))
    return '\n'.join(out) + '\n'


HEADER_ADD = """\
; Misfortune v2 = v1 (cells/misfortune.asm) + the checked refill + hold = 'off' + armed children.
; GENERATED by cells/gen_misfortune2.py -- do not edit by hand.  Written with AI help.
;   Checked refill: a bite stores SPLIT + d and the view offset of the bitten square in memory [%(act)d], [%(act1)d].  On the next
;   slow path (after the prefix clean) a stored dir whose snapshot square is EMPTY, with energy >= %(rmin)d, is played at once
;   (13 instructions).  The byte is cleared first on every path, so a child starts clean.  Other slow paths +2.
;   Prey hold off: an enemy on a diagonal square no longer holds a cell of energy >= %(smin)d (it takes the walker / split logic).
;   Armed children: a split at energy = 1 mod 4 with an enemy beside the child's square arms the child's slots (byte 8 =
;   the child's energy, bite = the child's own scan) so its first call bites in 2 instructions.
; Memory: v1's, plus [%(act)d] SPLIT + d (0 = none) and [%(act1)d] the view offset.
;
"""


def params():
    p = M.params()
    p.update({'act': MEM_ACT, 'act1': MEM_ACT + 1, 'rmin': REFILL_MIN, 'smin': G.SPLIT_MIN, 'e0': M.MEM_E0,
              'steps': B2.MEM_STEPS})
    return p


def generate():
    src = M.generate()
    k = src.index('\nstart:\n')
    head, body = src[:k], src[k:]
    p = params()
    prefix = M.PREFIX % p
    assert body.count(prefix) == 1
    assert body.count(ARM_FROM) == 1 and body.count('\narm:\n') == 1
    body = body.replace(prefix, prefix + REFILL % p)
    body = body.replace(ARM_FROM, ARM_TO % p)
    # hold = 'off': the threat block (hold, late split) becomes cmp / jae resume / steps = 0, then rest
    assert body.count(THREAT_BLOCK_FROM) == 1 and body.count(THREAT_BLOCK_END) == 1
    ta, tb = body.index(THREAT_BLOCK_FROM), body.index(THREAT_BLOCK_END)
    assert ta < tb
    body = body[:ta] + THREAT_TO % p + body[tb + 1:]
    assert body.count(RESUME_FROM) == 1
    body = body.replace(RESUME_FROM, 'resume:\n' + RESUME_FROM)
    # armed children: gate 1 and the emit path go through `child`
    assert body.count(GATE_FROM) == 1 and body.count(SPLIT_FROM) == 1
    body = body.replace(GATE_FROM, '\tjae\t\tchild\t\t\t\t; refill / split: 11 instructions, then block child\n')
    body = body.replace(SPLIT_FROM, '\tlea\t\teax, [r9 + ACT_SPLIT]\n' + CHILD % p)
    # Schism's boxed feed (feed_up..feed_left and the fallback's ret) is padded by FEED_PAD: a feed lifts a neighbour's energy
    # before its owner acts, so every feed must run after every armed-child split (min feed 94 + 6 = 100 > max split path)
    for d in ('up', 'right', 'down', 'left'):
        lab = 'feed_%s:\n' % d
        assert body.count(lab) == 1
        body = body.replace(lab, lab + '\ttimes %d %s\t\t; parity guard: slower than every armed-child split\n' % (FEED_PAD, M.FILL))
    fb = '\tja\t\trest\t\t\t\t; no friend (255), or the poorest is above the limit\n\tret\t\t\t\t\t; al = ACT_FEED + direction\n'
    assert body.count(fb) == 1
    body = body.replace(fb, fb.replace('\tret', '\ttimes %d %s\t\t; parity guard\n\tret' % (FEED_PAD, M.FILL)))
    # the cap-rule pad is fixed: 80 when nothing is stored (v1 padded for 0 extra instructions)
    old_fill = 'times %d %s' % (p['fill_hit'], p['fill'])
    assert body.count(old_fill) == 1
    body = body.replace(old_fill, 'times %d %s' % (p['fill_hit'] - 2, p['fill']))
    # row_tbl (1 KB) is replaced by row4_tbl (4 KB)
    a = body.index('row_tbl:')
    b = body.index('pat1_tbl:')
    body = body[:a] + row4_table() + body[b:]
    k = body.index('dir_tbl:')
    body = body[:k] + cbase_line() + body[k:]
    k = body.index('c2e_tbl:')
    body = body[:k] + cpat_table() + body[k:]
    head = head.replace('; Misfortune (cap B, exact 1): Bane v2.2 with', '; Misfortune v2 (cap B, exact 1): Bane v2.2 with', 1)
    head = head.replace(';\n; Paste this whole file', ';\n' + HEADER_ADD % p + '; Paste this whole file', 1)
    head = head.replace('GENERATED by cells/gen_misfortune.py', 'GENERATED by cells/gen_misfortune2.py', 1)
    return head + body


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'misfortune2.asm')
    src = generate()
    with open(out, 'w', newline='\n') as f:
        f.write(src)
    print('wrote %s (%d bytes source)' % (out, len(src.encode())))
