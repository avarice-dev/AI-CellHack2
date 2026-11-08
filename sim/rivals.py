"""Rival reference policies: plausible strong ladder cells, modelled on the replays.

Measured (data/ladder-data-2026-11-08.md section 4): every strong rival checks the four directions in a
fixed order (Hunter-style), so it bites in 4 / 6 / 8 / 10 by check order: Brawler-like U, L, R, D,
AtomPush-like R, L, U, D.  rbrawler, rpump and ratompush use that static front.  Hypothetical fronts,
kept for comparison only: rblind3 (bites at 3 in every direction), rlock5 / rfatgrab (checked lock +
pre-arm, 5 when locked) and rblindlock3 (blind lock, 9 then 3).  No measured rival uses a lock.

Each returns (action, insn, insn_no_taken_jumps) with the path counts an asm version would have (every
executed instruction incl. taken jumps and ret; the third value leaves taken jumps out, an indirect
`jmp [table]` counting as taken, as in cells_ref.py).  The asm below is a sketch written to get the
counts right, not a tested cell; each block's count is noted beside it.

Shared front, checked lock (designs.md 2.x "C"), memory byte 0:
    movsx rcx, byte [rdx]            ; lock: view offset of the target square, -100 based
    cmp   byte [rdi+rcx+100], 2      ; target square still holds an enemy?
    jne   .f6                        ; taken when unlocked (byte 0 -> view byte 100, always 0)
    mov   al, [rcx+eat_tbl+K]
    ret                              ; locked bite: 5 / 5
  .f6:                               ; lock miss 3 (alt 2)
    movdqu xmm0, [rdi+VIEW_CELLS+7] / pcmpeqb xmm0, [kEnemy] / pmovmskb eax, xmm0 / jmp [fight_tbl+rax*8]
                                     ; F6 4 (alt 3)
    fight stub: mov byte [rdx], LOCK_d / mov al, ACT_EAT+d / ret      ; 3 -> F6 bite 10 / 8
  Python stores the lock as 1 + direction (0 = none); the asm stores the view offset.  Same behaviour:
  self-checking, so a stale lock or an inherited one only costs the 3 lock-miss instructions.

Pre-arm (slow path, before anything else), no hit 7 / 7, hit 9 / 7:
    movdqu xmm1, [rdi+VIEW_CELLS+2] / pcmpeqb xmm1, [kFar] / pmovmskb ecx, xmm1 / test ecx, ecx / jnz .arm
    cmp byte [rdi+VIEW_CELLS+22], 2 / je .arm_down
    .arm: bsf ecx, ecx / mov cl, [arm_tbl+rcx] / mov [rdx], cl / jmp .grow     (.arm_down: mov, jmp)
  kFar = 2 at lanes 0, 8, 12 (view 2 = UP, 10 = LEFT, 14 = RIGHT); bsf order UP, LEFT, RIGHT, then DOWN.

Grow / feed tail (R-Lock5, R-Blind3):
    movzx esi, byte [rdi+VIEW_ENERGY] / cmp esi, SPLIT_MIN / jb .rest            ; 3 (alt 2 if taken)
    movdqu xmm2, [rdi+VIEW_CELLS+7] / pcmpeqb xmm2, [kEmpty] / pmovmskb ecx, xmm2 / test ecx, ecx / jz .feed
                                                                                 ; 5 (alt 4 if taken)
    split: movzx eax, byte [rdi+VIEW_RAND] / and eax, 3 / lea ecx, [rax+rcx*4] / mov al, [split_tbl+rcx]
           / ret                                                                 ; 5 (first empty from rand&3)
    .feed: cmp esi, FEED_MIN / jb .rest                                          ; 2 (alt 1 if taken)
    poorest friend neighbour (8, no jumps):
           movdqu xmm3, [rdi+VIEW_CELLS+7] / pcmpeqb xmm3, [kFriend] / pxor xmm3, [kOnes]
           / movdqu xmm4, [rdi+VIEW_ENERGIES+7] / por xmm4, xmm3 / pshufb xmm4, [kGather]
           / phminposuw xmm4, xmm4 / movd ecx, xmm4          ; non-friends read 255; ties -> U, R, D, L
    cmp cx, TARGET_MAX / ja .rest                                                ; 2 (alt 1 if taken)
    lea r9d, [rsi-MARGIN] / cmp r9w, cx / jb .rest                               ; 3 (alt 2 if taken)
    shr ecx, 16 / mov al, [feed_tbl+rcx] / ret                                   ; 3
    .rest: mov al, ACT_REST / ret                                                ; 2
"""

from engine import ACT_REST, ACT_SPLIT, ACT_EAT, ACT_FEED, CELL_ENEMY, CELL_EMPTY, CELL_FRIEND
from cells_ref import _sprint_bite

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
NB = (7, 13, 17, 11)                                   # view index of the neighbour in direction d
FAR_ORDER = ((2, UP), (10, LEFT), (14, RIGHT), (22, DOWN))   # pre-arm squares, bsf order
# view indices of the other three neighbours of neighbour d (the fourth is this cell)
NB_OF_NB = ((2, 6, 8), (8, 14, 18), (16, 18, 22), (6, 10, 16))


def _f6_bite(c):
    """Direction F6 would bite, or None.  Same priority as Sprint (cells_ref)."""
    enemies = [d for d in (0, 1, 2, 3) if c[NB[d]] == CELL_ENEMY]
    if enemies:
        return _sprint_bite(enemies)
    return None


def _prearm(c, mem, n, alt):
    for i, d in FAR_ORDER:
        if c[i] == CELL_ENEMY:
            mem[0] = 1 + d
            return n + 9, alt + 7
    return n + 7, alt + 7


def _feed_poorest(view, c, e, n, alt, margin, tmax):
    """Poorest friend neighbour (ties U, R, D, L) if e - margin >= its energy and it is <= tmax."""
    n += 8
    alt += 8
    en = view.energies
    best = 255
    bd = 0
    for d in (0, 1, 2, 3):
        i = NB[d]
        if c[i] == CELL_FRIEND and en[i] < best:
            best = en[i]
            bd = d
    n += 2
    if best > tmax:
        return ACT_REST, n + 2, alt + 3
    alt += 2
    n += 3
    if e - margin < best:
        return ACT_REST, n + 2, alt + 4
    return ACT_FEED + bd, n + 3, alt + 6


def _split_or(view, c, n, alt):
    """Energy already >= split min.  Returns (result or None, n, alt) after the empties block."""
    n += 5
    r = view.rand & 3
    for k in (0, 1, 2, 3):
        d = (r + k) & 3
        if c[NB[d]] == CELL_EMPTY:
            return (ACT_SPLIT + d, n + 5, alt + 10), n, alt
    return None, n, alt + 4


def _grow_feed(view, c, n, alt, split_min, feed_min, margin, tmax):
    e = view.energy
    n += 3
    if e < split_min:
        return ACT_REST, n + 2, alt + 4
    alt += 3
    res, n, alt = _split_or(view, c, n, alt)
    if res is not None:
        return res
    n += 2
    if e < feed_min:
        return ACT_REST, n + 2, alt + 3
    alt += 2
    return _feed_poorest(view, c, e, n, alt, margin, tmax)


# ---- fronts ------------------------------------------------------------------------------------------
_DIR_CODE = {'U': UP, 'R': RIGHT, 'D': DOWN, 'L': LEFT}


def parse_order(order):
    """'ULRD' -> ((7, UP), (11, LEFT), (13, RIGHT), (17, DOWN)): view index and direction per check."""
    ds = tuple(_DIR_CODE[ch] for ch in order.upper())
    if sorted(ds) != [0, 1, 2, 3]:
        raise ValueError('order must name each of U, R, D, L once: %r' % order)
    return tuple((NB[d], d) for d in ds)


def _make_front(front, order, prearm):
    """front(c, mem) -> (action, n, alt) for a bite, or (None, n, alt) with the slow path's start count.

    'static' (measured on the ladder, data/ladder-data-2026-11-08.md section 4), Hunter-style:
        cmp byte [rdi+VIEW_CELLS+idx_k], 2 / je .eat_k      ; 2 per check, in `order`
        .eat_k: mov al, ACT_EAT+d / ret                     ; bite at check k (0-3): 4 + 2k / 3 + 2k
        all four miss: 8 / 8; no memory use
    'lock': checked lock + F6 + optional pre-arm (see the module docstring), memory byte 0.
    """
    if front == 'static':
        checks = tuple((i, d, 4 + 2 * k, 3 + 2 * k) for k, (i, d) in enumerate(parse_order(order)))

        def static_front(c, mem):
            for i, d, n, alt in checks:
                if c[i] == CELL_ENEMY:
                    return ACT_EAT + d, n, alt
            return None, 8, 8
        return static_front
    if front == 'flat3':
        # hypothetical (R-Blind3): any adjacent enemy is bitten at 3 / 3, whatever its direction; no memory.
        # Several enemies: Sprint's priority.  A miss costs 8 / 8 like the static front.
        def flat3_front(c, mem):
            d = _f6_bite(c)
            if d is not None:
                return ACT_EAT + d, 3, 3
            return None, 8, 8
        return flat3_front
    if front == 'lock':
        def lock_front(c, mem):
            k = mem[0]
            if k and c[NB[k - 1]] == CELL_ENEMY:
                return ACT_EAT + k - 1, 5, 5
            d = _f6_bite(c)
            if d is not None:
                mem[0] = 1 + d
                return ACT_EAT + d, 10, 8
            if prearm:
                n, alt = _prearm(c, mem, 7, 5)
                return None, n, alt
            return None, 7, 5
        return lock_front
    raise ValueError("front must be 'static', 'flat3' or 'lock'")


# ---- feeding tails -----------------------------------------------------------------------------------
def _grow_pump(view, c, n, alt, split_min, pump_min, tmax, hold='view', target='richest'):
    """Pump: interior cells push energy uphill to the richest friend neighbour that is <= tmax; a cell
    that sees an enemy anywhere in its view (not adjacent: the front already handled that) holds.

    After the split check (no empty neighbour):
      movdqu x2 / pcmpeqb x2 / por / pmovmskb / test / jnz .rest     ; 8, enemy in view (alt 7 if taken)
      cmp esi, PUMP_MIN / jb .rest                                    ; 2 (alt 1 if taken)
      richest feedable friend (12, no jumps): movdqu xmm3, cells / pcmpeqb kFriend / pxor kOnes
          / movdqu xmm4, energies / movdqa xmm5, xmm4 / pcmpgtb xmm5, [kTmax] / por xmm3, xmm5
          / pxor xmm4, kOnes / por xmm4, xmm3 / pshufb kGather / phminposuw / movd ecx, xmm4
          (key = 255 - e for friends <= tmax, 255 otherwise; ties -> U, R, D, L)
      cmp cx, 255 / jae .rest                                         ; 2 (alt 1 if taken)
      shr ecx, 16 / mov al, [feed_tbl+rcx] / ret                      ; 3
    hold='none' leaves the enemy-in-view block out (8 / 8 fewer on the not-taken path); target='poorest' feeds the poorest
    friend <= tmax instead (same count: the key is e instead of 255 - e).
    """
    e = view.energy
    n += 3
    if e < split_min:
        return ACT_REST, n + 2, alt + 4
    alt += 3
    res, n, alt = _split_or(view, c, n, alt)
    if res is not None:
        return res
    if hold == 'view':
        n += 8
        if CELL_ENEMY in c:
            return ACT_REST, n + 2, alt + 9
        alt += 8
    n += 2
    if e < pump_min:
        return ACT_REST, n + 2, alt + 3
    alt += 14
    n += 14
    en = view.energies
    best = -1
    bd = 0
    poorest = target == 'poorest'
    for d in (0, 1, 2, 3):
        i = NB[d]
        if c[i] == CELL_FRIEND:
            v = en[i]
            if v <= tmax and (best < 0 or (v < best if poorest else v > best)):
                best = v
                bd = d
    if best < 0:
        return ACT_REST, n + 2, alt + 3
    return ACT_FEED + bd, n + 3, alt + 5


def _grow_fat(view, c, n, alt, split_min, assist_min, assist_poor, donor_min, margin, tmax):
    """FatGrab tail: split at split_min; boxed-in cells feed only as capped donors (>= donor_min) or as
    assist donors (>= assist_min) to a poor friend (< assist_poor) that has an empty neighbour.

      cmp esi, DONOR_MIN / jae .donor                       ; 2 (alt 1 if taken) -> poorest-friend feed
      cmp esi, ASSIST_MIN / jb .rest                        ; 2 (alt 1 if taken)
      assist block (20, one jz): empties mask over the view (movdqu, pcmpeqb, pmovmskb x2, shl, or = 8),
        poor-friend mask (movdqu, movdqa, pcmpgtb, movdqu, pcmpeqb, pand, pmovmskb = 7),
        pext r11, r8, kNbrBits / movzx r11d, byte [nbr_tbl+r11] / pext r10, r10, kDirBits / and r10d, r11d
        / jz .rest (5)
      mov al, [assist_tbl+r10] / ret                        ; 2  (first candidate in U, R, D, L order)
    """
    e = view.energy
    n += 3
    if e < split_min:
        return ACT_REST, n + 2, alt + 4
    alt += 3
    res, n, alt = _split_or(view, c, n, alt)
    if res is not None:
        return res
    return _fat_tail(view, c, e, n, alt, assist_min, assist_poor, donor_min, margin, tmax)


def _fat_tail(view, c, e, n, alt, assist_min, assist_poor, donor_min, margin, tmax):
    """_grow_fat after a split check that found no empty neighbour (e >= split_min)."""
    n += 2
    if e >= donor_min:
        return _feed_poorest(view, c, e, n, alt + 1, margin, tmax)
    alt += 2
    n += 2
    if e < assist_min:
        return ACT_REST, n + 2, alt + 3
    alt += 2
    n += 20
    en = view.energies
    for d in (0, 1, 2, 3):
        i = NB[d]
        if c[i] == CELL_FRIEND and en[i] < assist_poor:
            a, b, f = NB_OF_NB[d]
            if c[a] == CELL_EMPTY or c[b] == CELL_EMPTY or c[f] == CELL_EMPTY:
                return ACT_FEED + d, n + 2, alt + 22
    return ACT_REST, n + 2, alt + 21


def _padded(pol, pad):
    """pad > 0: every non-bite path costs `pad` more (both counts).  Models a slow cell whose bites were
    measured fast (direction profile) but whose match-page average is far above the model's
    (data/pull2/summaries facts 'insns': rooby 58-79, Noob++ 73-90, Aegis 32-35; the models run ~20).
    The name keeps the policy's own name."""
    if not pad:
        return pol

    def padded(view, mem):
        r = pol(view, mem)
        if r[0] & 0xF0 == ACT_EAT:
            return r
        return r[0], r[1] + pad, r[2] + pad
    padded.__name__ = pol.__name__
    return padded


# ---- rival families ----------------------------------------------------------------------------------
def make_rbrawler(order='ULRD', front='static', prearm=True, feed='poorest', split_min=5, feed_min=6,
                  feed_margin=2, feed_target_max=48, pump_min=16, pump_target_max=48, hold='view',
                  target='richest', pad=0):
    """Brawler-like (Striker): static front U, L, R, D (4/6/8/10, measured), split at 5.

    feed='poorest': heavy feeding, cells with e >= feed_min feed the poorest friend neighbour when the
      margin and target cap allow (aim: colony mean energy ~10-15, like Brawler in 98753).
    feed='pump': see _grow_pump (thin interior, fat front; Bouncer / Brawler v2 / Aegis / Noob+ style).
    Static-front paths, poorest feeding (insn / alt): bite 4/6/8/10 (alt 3/5/7/9); rest (e < 5) 13/12;
      split 21/21; boxed in, e < feed_min 20/17; feed 34/33; declined at the cap 30/28, margin 33/31.
    Pump: rest 13/12; split 21/21; enemy in view 26/24; e < pump_min 28/26; feed 43/42; declined 42/40.
    front='lock': see make_rlock5.
    """
    fr = _make_front(front, order, prearm)
    if feed == 'poorest':
        def rbrawler(view, mem):
            c = view.cells
            a, n, alt = fr(c, mem)
            if a is not None:
                return a, n, alt
            return _grow_feed(view, c, n, alt, split_min, feed_min, feed_margin, feed_target_max)
    elif feed == 'pump':
        def rbrawler(view, mem):
            c = view.cells
            a, n, alt = fr(c, mem)
            if a is not None:
                return a, n, alt
            return _grow_pump(view, c, n, alt, split_min, pump_min, pump_target_max, hold, target)
    else:
        raise ValueError("feed must be 'poorest' or 'pump'")
    return _padded(rbrawler, pad)


def make_rpump(**kw):
    """Brawler front + pump feeding (the upset winners' profile, ladder data section 3)."""
    kw.setdefault('feed', 'pump')
    return make_rbrawler(**kw)


def make_rlock5(**kw):
    """R-Lock5 (hypothetical): checked lock + pre-arm front with Brawler-like poorest feeding.

    Paths (insn / alt): locked bite 5/5; F6 bite 10/8; rest (e < 5) 19/16; split 27/25; no empty and
    e < feed_min 26/22; feed 40/37; declined at the cap 36/32, at the margin 39/35.  Pre-arm hit +2.
    """
    kw.setdefault('front', 'lock')
    return make_rbrawler(**kw)


def make_ratompush(order='RLUD', front='static', prearm=True, split_min=5, assist_min=10, assist_poor=5,
                   donor_min=48, feed_margin=2, feed_target_max=48, split_after=None, pad=0):
    """AtomPush-like (HammerSpb): static front R, L, U, D (measured), feed-assisted grab, fat body.

    Static-front paths: bite 4/6/8/10; rest (e < 5) 13/12; split 21/21; boxed in, e < assist_min 22/20;
    assist feed 42/41; assist found none 42/40; donor feed (e >= donor_min) 34/32, declined 30/28 (cap)
    or 33/31 (margin).  front='lock': see make_rfatgrab.
    split_after=k (static front only): the split check (movzx/cmp/jb 3, empties 5, split 5) comes after
    the first k direction checks, so a hole is refilled in 2k + 13 (k = 2: 17, below Sprint's 19-23;
    replay mining 2026-11-08: AtomPush takes 99% of contested holes from Sprint, child energy ~6).  A failed
    check costs 3 / 2 (e < split_min) or 8 / 7 (no empty) before the remaining direction checks.
    """
    if split_after is not None:
        if front != 'static' or not 0 <= split_after <= 4:
            raise ValueError('split_after needs the static front and 0..4 checks')
        checks = parse_order(order)
        first, rest = checks[:split_after], checks[split_after:]

        def ratompush_sa(view, mem):
            c = view.cells
            n = 0
            for i, d in first:
                if c[i] == CELL_ENEMY:
                    return ACT_EAT + d, n + 4, n + 3
                n += 2
            e = view.energy
            boxed = False
            if e < split_min:
                n, alt = n + 3, n + 2
            else:
                r = view.rand & 3
                for k in (0, 1, 2, 3):
                    d = (r + k) & 3
                    if c[NB[d]] == CELL_EMPTY:
                        return ACT_SPLIT + d, n + 13, n + 13
                n, alt = n + 8, n + 7
                boxed = True
            for i, d in rest:
                if c[i] == CELL_ENEMY:
                    return ACT_EAT + d, n + 4, alt + 3
                n += 2
                alt += 2
            if not boxed:
                return ACT_REST, n + 2, alt + 2
            return _fat_tail(view, c, e, n, alt, assist_min, assist_poor, donor_min, feed_margin,
                             feed_target_max)
        return _padded(ratompush_sa, pad)
    fr = _make_front(front, order, prearm)

    def ratompush(view, mem):
        c = view.cells
        a, n, alt = fr(c, mem)
        if a is not None:
            return a, n, alt
        return _grow_fat(view, c, n, alt, split_min, assist_min, assist_poor, donor_min, feed_margin,
                         feed_target_max)
    return _padded(ratompush, pad)


def make_rfatgrab(**kw):
    """R-FatGrab (hypothetical lock variant of ratompush): lock front + pre-arm.  Paths: locked 5/5;
    F6 10/8; rest 19/16; split 27/25; boxed in, e in [5, assist_min) 28/24; assist feed 48/45; none
    found 48/44; donor feed 40/36, declined 36/32 (cap) or 39/35 (margin)."""
    kw.setdefault('front', 'lock')
    return make_ratompush(**kw)


def make_rblind3(**kw):
    """R-Blind3 (hypothetical): bites at 3 in every direction (front='flat3'), Brawler-like body.

    No real rival is this fast (all measured fronts are direction-ordered 4/6/8+, ladder data s4); it is
    the upper bound a direction-free front could reach.  Slow paths as rbrawler (rest 13, split 21, ...).
    """
    kw.setdefault('front', 'flat3')
    return make_rbrawler(**kw)


def make_rblindlock3(split_min=5, feed_min=6, feed_margin=2, feed_target_max=48):
    """R-BlindLock3 (hypothetical, the earlier rblind3 model): blind lock `or al,[rdx]` / `jz .f6` / `ret` (rax = 0 at entry, verified).

    Memory byte 0 holds the eat action byte once the F6 path bites; from then on the cell returns it on
    every call and never does anything else (a no-op on an empty square; bites friends that step in).
    Paths: locked 3/3; F6 bite 9/7 (or, jz taken 2/1 + F6 4/3 + store, mov, ret 3); rest 11/8;
    split 19/17; no empty and e < feed_min 18/14; feed 32/29; feed declined at cap 28/24, margin 31/27.
    """
    def rblindlock3(view, mem):
        a = mem[0]
        if a:
            return a, 3, 3
        c = view.cells
        d = _f6_bite(c)
        if d is not None:
            mem[0] = ACT_EAT + d
            return ACT_EAT + d, 9, 7
        return _grow_feed(view, c, 6, 4, split_min, feed_min, feed_margin, feed_target_max)
    return rblindlock3


# name -> factory(**params) -> policy.  Tuned variants via policies.get('rpump[pump_min=12]').
FACTORIES = {
    'rbrawler': make_rbrawler,      # measured front U,L,R,D + poorest-friend feeding
    'rpump': make_rpump,            # measured front U,L,R,D + pump feeding
    'ratompush': make_ratompush,    # measured front R,L,U,D + FatGrab economy
    'rlock5': make_rlock5,          # hypothetical: lock front + Brawler feeding
    'rfatgrab': make_rfatgrab,      # hypothetical: lock front + FatGrab economy
    'rblind3': make_rblind3,        # hypothetical: bites at 3 in every direction
    'rblindlock3': make_rblindlock3,  # hypothetical: blind lock (first bite 9, then 3, never exits)
}

rbrawler = make_rbrawler()
rpump = make_rpump()
ratompush = make_ratompush()
rlock5 = make_rlock5()
rfatgrab = make_rfatgrab()
rblind3 = make_rblind3()
rblindlock3 = make_rblindlock3()
