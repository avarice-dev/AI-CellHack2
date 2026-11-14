"""Generate cells/depravity.asm ("Depravity": a clean-sheet cell built on the Misfortune v2 arm_tbl variant).

    python cells/gen_depravity.py     # writes cells/depravity.asm next to this file

Locked spec: shared/cellhack2/PLAN.md.  Reference policy: sim/cells_ref.make_depravity().  Built on
gen_misfortune2.generate(armtbl=True) (arm_tbl pattern of commit aee07dd, gate 1, threat / hold_split, walker) with:
 - no cap B (hold / lift / pull logic and the 80-instruction padding are deleted);
 - HOLD_MIN = 8 (hold_split from e >= 8);
 - k = 0 rows (te <= 2) arm slots e0 - 4, e0 - 2, e0 only (the stun-save); k = 1..5 unchanged;
 - settled split: "first 8/2 dir-open" (tools/search/opening_search.py): the empty neighbour with the fewest friends on
   its side plus a non-empty square beyond it, ties in rotation order (start at the bearing for a first child, one
   past it for later children); steps = 8 for a first child that goes forward, else 2; popcount by the 256-byte
   pop8_tbl (no popcnt, SSE2 only);
 - boxed: below T_FEED = 200 only a capped donor (e >= 47) feeds its poorest friend (<= 46); from T_FEED the
   Scourge / Bane2 boxed block (edge friend with an empty edge, then the poorest friend).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sprint as G  # noqa: E402
import gen_bane2 as B2  # noqa: E402
import gen_misfortune as M  # noqa: E402
import gen_misfortune2 as G2  # noqa: E402

HOLD_MIN = 8
T_FEED = 200
FEED_CAP = 47               # below T_FEED: only e >= 47 feeds (poorest friend <= 46)
K_LONG, K_SHORT = 8, 2

# view squares on each side beyond the neighbour UP, RIGHT, DOWN, LEFT (tools/search/opening_search.py SIDE / BEYOND)
SIDE = {0: (0, 1, 2, 3, 4, 6, 8), 1: (4, 9, 14, 19, 24, 8, 18), 2: (20, 21, 22, 23, 24, 16, 18),
        3: (0, 5, 10, 15, 20, 6, 16)}
BEYOND = (2, 14, 22, 10)
IDX = B2.DIR_IDX            # (7, 13, 17, 11)
DIRN = ('up', 'right', 'down', 'left')


def side_mask(d):
    return sum(1 << i for i in SIDE[d])


def pattern_row(d, k):
    """16 bytes for slots e0 - 4 .. e0 + 11: EAT + d on the even offsets up to 2k.  k = 0 (te <= 2): slots e0 - 4,
    e0 - 2, e0 only (stun-save), instead of Misfortune's empty row."""
    return bytes((G.ACT_EAT + d) if (j - M.LOW) % 2 == 0 and j - M.LOW <= 2 * k else 0 for j in range(16))


def pop_ops(d):
    """Instruction lines that leave popcount(F & SIDE[d]) in r10d (r8d = F; edx is consumed)."""
    mask = side_mask(d)
    nz = [k for k in range(4) if mask >> (8 * k) & 0xFF]
    assert mask >> 25 == 0 and (mask >> 24 & 1) <= 1
    out = ['\tmov\t\tedx, r8d', '\tand\t\tedx, 0x%x' % mask]
    shifted, first = 0, True
    for k in nz:
        if 8 * k > shifted:
            out.append('\tshr\t\tedx, %d' % (8 * k - shifted))
            shifted = 8 * k
        byte = mask >> (8 * k) & 0xFF
        if k == nz[-1] and byte == 1:               # last byte, a single bit 0: edx is already 0 / 1
            out.append('\tmov\t\tr10d, edx' if first else '\tadd\t\tr10d, edx')
        elif first:
            out += ['\tmovzx\t\tr10d, dl', '\tmovzx\t\tr10d, byte [abs pop8_tbl + r10]']
        else:
            out += ['\tmovzx\t\teax, dl', '\tmovzx\t\teax, byte [abs pop8_tbl + rax]', '\tadd\t\tr10d, eax']
        first = False
    return out


def pop_count(d):
    """Number of instructions of pop_ops(d) (the reference's per-direction cost)."""
    return len(pop_ops(d))


def settled_asm():
    L = ['settled:',
         '\tcmp\t\tesi, 5',
         '\tjb\t\trest',
         '\tmovdqu\t\txmm1, [rdi + VIEW_CELLS]\t; friends of the 25 squares: bit i = view idx i',
         '\tmovdqu\t\txmm2, [rdi + VIEW_CELLS + 9]',
         '\tpcmpeqb\t\txmm1, [kOne]',
         '\tpcmpeqb\t\txmm2, [kOne]',
         '\tpmovmskb\tr8d, xmm1',
         '\tpmovmskb\tr10d, xmm2',
         '\tshl\t\tr10d, 9',
         '\tor\t\tr8d, r10d\t\t\t; r8d = friend mask F (25 bits)',
         '\tmovzx\t\teax, byte [abs CELLMEM_BASE + %d]' % B2.MEM_BEAR,
         '\tand\t\teax, 3',
         '\tmov\t\tr9d, 4',
         '\tsub\t\tr9d, eax\t\t\t; r9d = 4 - bearing: rotation position of d is (d + r9d) & 3',
         '\tcmp\t\tecx, [abs CELLMEM_BASE + %d]' % B2.MEM_POS,
         '\tjne\t\tsd_first',
         '\tdec\t\tr9d\t\t\t\t; not the first child from this square: start one past the bearing',
         'sd_first:',
         '\tmov\t\tr11d, 255\t\t\t; best key = score * 4 + rotation position']
    for d, nm in enumerate(DIRN):
        L += ['\tcmp\t\tbyte [rdi + VIEW_CELLS + %d], CELL_EMPTY\t; %s' % (IDX[d], nm),
              '\tjne\t\tsd_skip_%s' % nm]
        L += pop_ops(d)
        L += ['\tcmp\t\tbyte [rdi + VIEW_CELLS + %d], CELL_EMPTY\t; the square beyond' % BEYOND[d],
              '\tje\t\tsd_be_%s' % nm,
              '\tinc\t\tr10d',
              'sd_be_%s:' % nm,
              '\tlea\t\teax, [r9 + %d]' % d,
              '\tand\t\teax, 3',
              '\tlea\t\tr10d, [rax + r10*4]',
              '\tcmp\t\tr11d, r10d',
              '\tcmova\t\tr11d, r10d',
              'sd_skip_%s:' % nm]
    L += ['\ttest\t\tr11b, 3\t\t\t; rotation position 0 = the start square (the bearing, for a first child)',
          '\tjnz\t\tsd_short',
          '\tcmp\t\tecx, [abs CELLMEM_BASE + %d]' % B2.MEM_POS,
          '\tje\t\tsd_short',
          '\tmov\t\tbyte [abs CELLMEM_BASE + %d], %d\t; first child, forward: long walk' % (B2.MEM_STEPS, K_LONG),
          '\tjmp\t\tsd_store',
          'sd_short:',
          '\tmov\t\tbyte [abs CELLMEM_BASE + %d], %d' % (B2.MEM_STEPS, K_SHORT),
          'sd_store:',
          '\tand\t\tr11d, 3',
          '\tsub\t\tr11d, r9d',
          '\tand\t\tr11d, 3\t\t\t; d',
          '\tmov\t\t[abs CELLMEM_BASE + %d], r11b' % B2.MEM_BEAR,
          '\tmov\t\t[abs CELLMEM_BASE + %d], ecx' % B2.MEM_POS,
          '\tlea\t\teax, [r11 + ACT_SPLIT]',
          '\tret']
    return '\n'.join(L) + '\n'


BOXED_HEAD = """\
boxed:
	cmp		dword [rdi + VIEW_TICK], %(tfeed)d
	jae		boxed_std			; from T_FEED: the standard boxed block
	cmp		esi, %(cap)d
	jb		rest				; below T_FEED only a capped donor feeds
	jmp		fallback			; poorest friend <= 46
boxed_std:
"""

HEADER = """\
; Depravity: clean-sheet cell (Misfortune v2 arm_tbl core, no cap B), for CellHack2.
; GENERATED by cells/gen_depravity.py -- do not edit by hand.  Written with AI help.  Spec: shared/cellhack2/PLAN.md.
;
; Paste this whole file into the site.  It has no org/bits/section/%%include on purpose: the server
; prepends `bits 64 / org CODE_BASE / default rel / <cellhack.inc>` and runs `nasm -f bin`.
; CPU target: plain qemu64 (SSE2 only; no VEX, no popcnt).  No loops, no stack use.
; Relies on: rax = 0 and xmm0 = 0 at entry, esi = own energy.  Every access indexed by my energy uses esi (0x67 prefix).
;
; Memory: [0] bearing, [1] steps left, [4..7] x | y << 16 of the square this cell last split from; [8] e0 (0 = unarmed);
; [13 + e] = slot(e), e = 0..50 (byte 63 = slot 50, always 0): non-zero = the EAT action to play at energy e.
;
; Paths (every executed instruction): armed bite 2; first bite (arm, arm_tbl stubs) 17; gate 1 refill / split 15;
;   enemy on a diagonal, e >= %(hmin)d: split 29 (hold_split).  Walker, settled dir-open split and boxed counts:
;   see sim/cells_ref.make_depravity() and the check_cells output.
;   k = 0 (te <= 2) arms only slots e0 - 4, e0 - 2, e0 (stun-save).  Below T_FEED = %(tfeed)d the boxed block feeds only
;   from e >= %(cap)d (poorest friend <= 46).
;
"""


def generate():
    saved = G2.HOLD_MIN
    G2.HOLD_MIN = HOLD_MIN
    try:
        src = G2.generate(armtbl=True)
    finally:
        G2.HOLD_MIN = saved
    p = {'hmin': HOLD_MIN, 'tfeed': T_FEED, 'cap': FEED_CAP}
    k = src.index('\nstart:\n')
    body = src[k:]
    head = HEADER % p
    # settled block (Bane v2.2's rotation) -> dir-open
    a, b = body.index('\nsettled:\n') + 1, body.index('\nthreat:\n') + 1
    body = body[:a] + settled_asm() + body[b:]
    # cap_hit padding
    a, b = body.index('cap_hit:\n'), body.index('boxed:\n')
    assert body[a:b].count('\n') == 3
    body = body[:a] + body[b:]
    # cap B test -> T_FEED head
    cap = M.CAP % M.params()
    assert body.count('boxed:\n' + cap) == 1
    body = body.replace('boxed:\n' + cap, BOXED_HEAD % p)
    # constants / tables
    ring, dix = body.index('kRingE1:'), body.index('dir_idx:')
    body = body[:ring] + 'kOne:\ttimes 16 db 1\t\t; friend lanes\n' + body[dix:]
    a, a2 = body.index('pat1_tbl:'), body.index('\n; ---- bite_tbl')
    rows = ['pat1_tbl:\t\t\t; 16-byte rows (d, k): slots e0 - 4 .. e0 + 11 (k = 0: e0 - 4, e0 - 2, e0)']
    for d in range(4):
        for kk in range(M.K_MAX + 1):
            rows.append('\tdb %s\t; d %d, k %d' % (', '.join('0x%02x' % x for x in pattern_row(d, kk)), d, kk))
    rows.append(M._db('pop8_tbl', [bin(i).count('1') for i in range(256)], 'popcount of a byte', per=32))
    body = body[:a] + '\n'.join(rows) + '\n' + body[a2:]
    return head + body


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'depravity.asm')
    src = generate()
    with open(out, 'w', newline='\n') as f:
        f.write(src)
    print('wrote %s (%d bytes source)' % (out, len(src.encode())))
