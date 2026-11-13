"""Generate cells/misfortune.asm (the "Misfortune" cell, cap B, exact 1).  Tables are never written by hand.

    python cells/gen_misfortune.py     # writes cells/misfortune.asm next to this file

Misfortune is Bane v2.2 (cells/gen_bane2.py) with an energy-indexed blind bite instead of the checked stored bite.
Reference: sim/cells_ref.make_misfortune(cap='B', exact=1); spec: briefs/misfortune-spec-2026-11-13.md; listing:
briefs/misfortune-build-review-2026-11-13.md, section b.  Only cap B / exact 1 is built (no cap A or N code).

Memory: Bane v2.2's [0] bearing, [1] steps, [4..7] position; [8] e0 (the energy at the last arming);
[13 + e] = slot(e), e = 0..50 (byte 63 = slot 50): non-zero = the EAT action to play at energy e.

  entry   or al, [esi + slot 0] / jnz EXIT_ADDR                     armed bite: 2
  prefix  movzx ecx, [8] / movdqu [rcx + 9], xmm0                    zeroes the last armed window (xmm0 = 0 at entry)
  scan    Bane's `or al, [bite_tbl + rcx]` / jnz arm                 slow paths = Bane v2.2 core + 4
  arm     [8] = e0; one 16-byte pattern row (direction, k) to bytes 9 + e0 .. 24 + e0; byte 63 = 0: first bite 19
  boxed   cap B rule ahead of Bane's boxed block: hold (EAT an edge friend at 48+ with an enemy on its edges), else
          lift (FEED an edge friend at 47+ with an empty edge and no enemy on its edges; my energy >= 6).
          A hit is padded to 80 instructions; a miss costs exactly 56 (the reference's 6 per edge + 8 per edge).

The cap test is branch-free.  Two SSE compares give the enemy / empty lanes of the 7 ring squares 6, 8, 10, 14
(window idx 0..15) and 16, 18, 22 (window idx 9..24); square 2 comes from a word table into lane 15.  ring_e /
ring_z map the 10 lane bits 6..15 to a byte, the four edge energies map through en_tbl, and
    idx = ring_e[E] & ring_z[Z] & (en_U | en_R | en_D | en_L) & e6[esi]
has the hold edges in bits 0..3 and the lift edges in bits 4..7 (ring_e = Er | ~Er << 4, ring_z = Zr << 4 | 0x0F,
en = (e >= 48) << d | (e >= 47) << (d + 4), e6 = 0xFF from my energy 6, else 0x0F).  cap_tbl[idx] is the action.
An edge square on the boxed path is a friend or a wall, and a wall has energy 0 (docs/cellhack.inc), so the energy
test also stands in for the friend test.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sprint as G  # noqa: E402
import gen_bane2 as B2  # noqa: E402

MEM_E0, SLOT0 = 8, 13
LOW, HIGH = 4, 10           # armed slots lie in e0 - 4 .. e0 + 10
K_MAX = 5                   # k = min(5, (te + 1) // 2 - 1): 2k <= HIGH
HOLD_MIN, LIFT_MIN, FEED_MIN = 48, 47, 6
PULL_N = 80                 # a cap-rule action takes exactly this many instructions
CAP_MISS_N = 56             # a missed cap rule: 4 x 6 (hold pass) + 4 x 8 (lift pass), as the reference counts
BOXED_AT = 17               # instructions executed before the label `boxed` (entry 2, prefix 2, scan 5, gate 1 8)
CAP_TEST_N = 31             # the branch-free test, up to and including `jnz cap_hit`
FILL = 'xor\t\tr11d, r11d'  # filler instruction (r11 is not used elsewhere)

RING = {0: (2, 6, 8), 1: (8, 14, 18), 2: (16, 18, 22), 3: (6, 10, 16)}    # edges of the friend UP, RIGHT, DOWN, LEFT
LANE_LO = (6, 8, 10, 14)    # squares read from window idx 0..15 (lane = idx)
LANE_HI = (16, 18, 22)      # squares read from window idx 9..24 (lane = idx - 9)
LANE = {6: 6, 8: 8, 10: 10, 14: 14, 16: 7, 18: 9, 22: 13, 2: 15}       # square -> lane of the merged mask
ENERGY_OFF = tuple(64 + i for i in B2.DIR_IDX)   # VIEW_ENERGIES = 64: view offset of the neighbour's energy


def k_of(te):
    """Bites still needed after this one for an unfed target of energy te (the asm masks te with 63), at most 5."""
    return max(0, min(K_MAX, ((te & 63) + 1) // 2 - 1))


def row_index(te, d):
    return d * (K_MAX + 1) + k_of(te)


def pattern_row(d, k):
    """16 bytes for slots e0 - 4 .. e0 + 11: EAT + d on the even offsets up to 2k (k = 0: nothing)."""
    return bytes((G.ACT_EAT + d) if k > 0 and (j - LOW) % 2 == 0 and j - LOW <= 2 * k else 0 for j in range(16))


def ring_bits(mask10):
    """The 4-bit set of edges whose ring has a square with its bit set in the 10-bit lane mask (lanes 6..15)."""
    out = 0
    for d, sq in RING.items():
        if any(mask10 >> (LANE[s] - 6) & 1 for s in sq):
            out |= 1 << d
    return out


def ring_e(m):
    er = ring_bits(m)
    return er | ((~er) & 15) << 4


def ring_z(m):
    return ring_bits(m) << 4 | 0x0F


def en_value(d, e):
    return (1 << d if e >= HOLD_MIN else 0) | (1 << (d + 4) if e >= LIFT_MIN else 0)


def e6_value(e):
    return 0xFF if e >= FEED_MIN else 0x0F


def cap_action(idx):
    hold, lift = idx & 15, idx >> 4
    for d in range(4):
        if hold >> d & 1:
            return G.ACT_EAT + d
    for d in range(4):
        if lift >> d & 1:
            return 0x40 + d                       # ACT_FEED
    return 0


def lane_const(squares, offset, match):
    b = [0xFF] * 16
    for s in squares:
        b[s - offset] = match
    return ', '.join('0x%02x' % x for x in b)


def _db(name, values, comment, per=64):
    vals = list(values)
    out = ['%s:\t\t\t; %s' % (name, comment)]
    for i in range(0, len(vals), per):
        out.append('\tdb %s' % ','.join('%d' % v for v in vals[i:i + per]))
    return '\n'.join(out)


def _dw(name, values, comment, per=32):
    vals = list(values)
    out = ['%s:\t\t\t; %s' % (name, comment)]
    for i in range(0, len(vals), per):
        out.append('\tdw %s' % ','.join('%d' % v for v in vals[i:i + per]))
    return '\n'.join(out)


def tables():
    out = ['dir_tbl:\tdb %s\t; view offset of the energy of the neighbour UP, RIGHT, DOWN, LEFT' % ', '.join(
        '%d' % i for i in ENERGY_OFF)]
    out.append(_db('row_tbl', [row_index(i >> 2, i & 3) for i in range(1024)],
                   'pattern row d * 6 + k by te * 4 + d (te 0..255; k from te & 63)'))
    out.append('pat1_tbl:\t\t\t; 16-byte rows (d, k): slots e0 - 4 .. e0 + 11')
    for d in range(4):
        for k in range(K_MAX + 1):
            out.append('\tdb %s\t; d %d, k %d' % (', '.join('0x%02x' % x for x in pattern_row(d, k)), d, k))
    out.append(_dw('c2e_tbl', [0x8000 if c == 2 else 0 for c in range(256)], 'square 2 holds an enemy: lane 15'))
    out.append(_dw('c2z_tbl', [0x8000 if c == 0 else 0 for c in range(256)], 'square 2 is empty: lane 15'))
    out.append(_db('ring_e', [ring_e(m) for m in range(1024)], 'enemy lanes 6..15 -> Er | ~Er << 4'))
    out.append(_db('ring_z', [ring_z(m) for m in range(1024)], 'empty lanes 6..15 -> Zr << 4 | 0x0F'))
    for d, n in enumerate(('en_up', 'en_right', 'en_down', 'en_left')):
        out.append(_db(n, [en_value(d, e) for e in range(256)], 'edge friend energy -> hold / lift bits'))
    out.append(_db('e6_tbl', [e6_value(e) for e in range(256)], 'my energy: lift allowed from %d' % FEED_MIN))
    out.append(_db('cap_tbl', [cap_action(i) for i in range(256)], 'hold bits 0..3, lift bits 4..7 -> action'))
    return '\n'.join(out) + '\n'


def constants():
    return ('kRingE1:\tdb %s\t; idx 0..15: 2 at 6, 8, 10, 14\n' % lane_const(LANE_LO, 0, 2)
            + 'kRingE2:\tdb %s\t; idx 9..24: 2 at 16, 18, 22\n' % lane_const(LANE_HI, 9, 2)
            + 'kRingZ1:\tdb %s\t; idx 0..15: 0 at 6, 8, 10, 14\n' % lane_const(LANE_LO, 0, 0)
            + 'kRingZ2:\tdb %s\t; idx 9..24: 0 at 16, 18, 22\n' % lane_const(LANE_HI, 9, 0))


HEADER = """\
; Misfortune (cap B, exact 1): Bane v2.2 with an energy-indexed blind bite, for CellHack2.
; GENERATED by cells/gen_misfortune.py -- do not edit by hand.  Written with AI help.
;
; Paste this whole file into the site.  It has no org/bits/section/%%include on purpose: the server
; prepends `bits 64 / org CODE_BASE / default rel / <cellhack.inc>` and runs `nasm -f bin`.
; CPU target: plain qemu64 (SSE2 only used; no VEX).  No loops, no stack use.
; Relies on: rax = 0 and xmm0 = 0 at entry (registers are reset before every call; site probes calib-q / calib-r),
; esi = own energy.  Every access indexed by my energy uses esi (address-size prefix), not rsi.
; The cell memory is addressed as [abs CELLMEM_BASE + n].  The pattern store (e0 >= 40) and the prefix (e0 >= 40)
; write up to byte 74: bytes 64.. are scratch (mapped, not kept).
;
; Memory: [0] bearing, [1] steps left, [4..7] x | y << 16 of the square this cell last split from (Bane v2.2);
; [%(e0)d] e0, the energy at the last arming; [%(s0)d + e] slot(e) for e = 0..50 (byte 63 = slot 50).
;
; Behaviour
;   0. Armed bite: slot(my energy) is non-zero: play it without reading the view (2 instructions).
;   1. Every other path first zeroes the 16 bytes 9 + e0 .. 24 + e0 (the last armed window).
;   2. An enemy next to me: bite it (Bane's choice) and arm: [%(e0)d] = e0, slots e0 - 4 .. e0 + 2k of e0's parity hold
;      the same bite, k = min(5, (te + 1) // 2 - 1) the bites an unfed target of energy te still needs (k = 0: none);
;      slot 50 is cleared: 19 instructions.
;   3..5: Bane v2.2 (refill, split, prey hold with an enemy on a diagonal square, walkers), each path 4 instructions
;      longer than Bane v2.2's core (Bane v2.3a - 1).
;   6. No empty neighbour: cap B.  EAT the first edge friend (UP, RIGHT, DOWN, LEFT) at %(hold)d+ with an enemy on its
;      edges (hold it, armed); else FEED the first edge friend at %(lift)d+ with an empty edge and no enemy on its edges
;      (lift it to 50) when my energy >= %(feed)d.  Either is padded to %(pull)d instructions.  Otherwise Bane's boxed block,
;      %(miss)d instructions later.
"""

PREFIX = """\
	or		al, [esi + CELLMEM_BASE + %(s0)d]	; rax = 0 at entry: al = slot(my energy)
	jnz		EXIT_ADDR			; armed bite: 2 instructions
	movzx		ecx, byte [abs CELLMEM_BASE + %(e0)d]	; e0 of the last arming
	movdqu		[rcx + CELLMEM_BASE + 9], xmm0	; zero slots e0 - 4 .. e0 + 11 (xmm0 = 0 at entry)
"""
BITE = ("\tor\t\tal, [abs bite_tbl + rcx]\t; al = eat action, ZF = no enemy\n"
        "\tjnz\t\tarm\t\t\t\t; bite, and arm the slots for the next ticks\n")
ARM = """\
arm:
	mov		[abs CELLMEM_BASE + %(e0)d], sil	; e0
	movzx		edx, byte [abs dir_tbl - ACT_EAT + rax]	; view offset of the target's energy
	movzx		edx, byte [rdi + rdx]		; te
	lea		edx, [rax + rdx*4 - ACT_EAT]	; te * 4 + d
	movzx		edx, byte [abs row_tbl + rdx]	; d * 6 + k
	shl		edx, 4
	movdqu		xmm1, [abs pat1_tbl + rdx]
	movdqu		[esi + CELLMEM_BASE + 9], xmm1	; slots e0 - 4 .. e0 + 11 (bytes past 63: scratch)
	mov		byte [abs CELLMEM_BASE + 63], 0	; cap B: slot 50 never armed
	ret					; first bite: 19
"""
CAP = """\
	movdqu		xmm1, [rdi + VIEW_CELLS]	; cap B rule (branch-free): view idx 0..15
	movdqu		xmm2, [rdi + VIEW_CELLS + 9]	; view idx 9..24
	movdqa		xmm3, xmm1
	movdqa		xmm4, xmm2
	pcmpeqb		xmm1, [kRingE1]			; enemy at 6, 8, 10, 14
	pcmpeqb		xmm2, [kRingE2]			; enemy at 16, 18, 22
	pcmpeqb		xmm3, [kRingZ1]			; empty at 6, 8, 10, 14
	pcmpeqb		xmm4, [kRingZ2]			; empty at 16, 18, 22
	por		xmm1, xmm2
	por		xmm3, xmm4
	pmovmskb	r8d, xmm1			; enemy lanes 6..14
	pmovmskb	r9d, xmm3			; empty lanes 6..14
	movzx		r10d, byte [rdi + VIEW_CELLS + 2]
	or		r8w, [abs c2e_tbl + r10*2]	; square 2: lane 15
	or		r9w, [abs c2z_tbl + r10*2]
	shr		r8d, 6
	shr		r9d, 6
	movzx		r8d, byte [abs ring_e + r8]	; Er | ~Er << 4
	and		r8b, [abs ring_z + r9]		; & Zr << 4 | 0x0F
	movzx		r9d, byte [rdi + VIEW_ENERGIES + VIEW_UP]
	movzx		r10d, byte [abs en_up + r9]
	movzx		r9d, byte [rdi + VIEW_ENERGIES + VIEW_RIGHT]
	or		r10b, [abs en_right + r9]
	movzx		r9d, byte [rdi + VIEW_ENERGIES + VIEW_DOWN]
	or		r10b, [abs en_down + r9]
	movzx		r9d, byte [rdi + VIEW_ENERGIES + VIEW_LEFT]
	or		r10b, [abs en_left + r9]
	and		r10b, [esi + e6_tbl]		; lift needs my energy >= %(feed)d
	and		r8d, r10d			; hold edges bits 0..3, lift edges bits 4..7
	or		al, [abs cap_tbl + r8]		; al = 0 here: the action, ZF = no rule
	jnz		cap_hit
	times %(fill_miss)d %(fill)s		; a miss costs %(miss)d, as the reference counts it
"""
CAP_HIT = """\
cap_hit:
	times %(fill_hit)d %(fill)s		; pad the pull / lift to %(pull)d instructions
	ret
"""


def params():
    fill_miss = CAP_MISS_N - CAP_TEST_N
    fill_hit = PULL_N - (BOXED_AT + CAP_TEST_N) - 1
    return {'e0': MEM_E0, 's0': SLOT0, 'hold': HOLD_MIN, 'lift': LIFT_MIN, 'feed': FEED_MIN, 'pull': PULL_N,
            'miss': CAP_MISS_N, 'fill_miss': fill_miss, 'fill_hit': fill_hit, 'fill': FILL}


def generate():
    src = B2.generate()
    k = src.index('\nstart:\n')
    body = src[k:]
    p2 = B2.params()
    lock, setlock = B2.LOCK % p2, B2.SETLOCK % p2
    lockoff = [l for l in body.split('\n') if l.startswith('lock_off:')]
    assert body.count(lock) == 1 and body.count(setlock) == 1 and body.count(B2.BITE_TO) == 1 and len(lockoff) == 1
    assert body.count('\nboxed:\n') == 1 and body.count('\ndir_idx:') == 1
    p = params()
    body = body.replace(lock, PREFIX % p).replace(B2.BITE_TO, BITE).replace(setlock, ARM % p + CAP_HIT % p)
    body = body.replace('\nboxed:\n', '\nboxed:\n' + CAP % p)
    body = body.replace('\ndir_idx:', '\n' + constants() + 'dir_idx:')
    body = body.replace(lockoff[0] + '\n', tables())
    body = body.replace('slow:\t\t\t\t\t\t; 10 instructions so far', 'slow:\t\t\t\t\t\t; 9 instructions so far')
    return HEADER % p + body


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'misfortune.asm')
    src = generate()
    with open(out, 'w', newline='\n') as f:
        f.write(src)
    print('wrote %s (%d bytes source)' % (out, len(src.encode())))
