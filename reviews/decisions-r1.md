# Round 1 decisions (2026-11-07)

Reviews: `r1-rules.md` (R), `r1-strategy.md` (S), `r1-asm.md` (X). One line per suggestion:
accept / partial / reject, and why. New fact used here: the real bot sources (`docs/bots/`).

## Bot facts (from docs/bots/*.asm, counting every executed instruction incl. taken jumps and ret)
- Hunter: eat UP 7, RIGHT 10, DOWN 13, LEFT 16; rest (e<6) 17; split (e>=6, random dir) 20.
  It tries to split in a random direction even into occupied squares, so blocked interior cells with
  e>=6 never rest: Hunter colonies stall at ~6 energy per cell once packed.
- Medic: rest 6; split 9 (6<=e<15) or 13; feed-up 9 (e>=15, friend above). Never eats.
- Walker: split 7 (e>=6), rest 7, move 9. Random: rest 4 (e<6), else 14 (random move/split/eat/feed).
- Idle: rest 2 (one cell forever).
- Consequence: a static check in the order DOWN, LEFT, UP, RIGHT (4/6/8/10) acts before Hunter in
  every direction (Hunter's U/R/D/L are our D/L/U/R: 4<7, 6<10, 8<13, 10<16). The usual U,R,D,L
  order would lose to Hunter's UP (8 vs 7).

## Rules review (R)
- R1 accept: eating is income for the eater (+min(2, e)); "rest is the only income" holds only for
  the world as a whole. Fix 1.1 and Reaper text.
- R2 accept: prey rule must cover the parent's remaining energy too, not only the child.
- R3 accept: energy at the frontier is the growth throttle (each step costs 3-4 ticks of rest).
  Rewrite 1.1.2; grab needs early outward feeding (see S5).
- R4 accept: END is hard-coded 3000 (no constant exists); last-tick births can be eaten the same tick
  and whether they count is unverified. Fix kernel text.
- R5 accept: a death-freed square can be entered only next tick. Fix C.
- R6 accept: optimise placement (3/2/1/0), not margin; bot mix per match is unknown.
- R7 accept: one faster neighbour is enough to stun; path asymmetry handled by the D,L,U,R order
  (bot facts above) and by measuring contact directions in the simulator.
- R8 partial: never feed from e<=2 (accept); keep front cells fat proactively so feed-before-bite
  rarely matters; a dedicated short emergency-feed path only if the simulator shows deaths from it.
- R9 accept as candidate: `or al,[rdx]` / `jz full` / `ret` = 3-instruction lock if rax=0 at entry
  (verify), else 4. Goes into C's option list.
- R10 accept: use VIEW_AGE==0 to detect a newborn; parent writes its split direction before
  returning so the child knows where it came from (verify memory copy happens after the call).
- R11 accept: contested empty squares need a free tie-break (parity of x+y+tick or a direction rule).
- R12 accept: never feed a target >=49; REST at 50 is waste; EAT at 50 is denial only.
- R13 accept: SSE2/SSE3 only, `align 16` for legacy-SSE memory operands; drop "do ret/jumps count"
  from 1.3 (the Reference says every instruction is counted); keep `rep` granularity open.
- R14 partial: walking fat cells as an energy conveyor is plausible; test in the simulator before
  adopting (holes cost population).
- R15 accept: merged into 1.3.

## Strategy review (S)
- S1 accept: the front-path count is the top priority.
- S2 partial: direction dependence is real, but against the known Hunter the D,L,U,R order already
  wins everywhere; against tuned opponents, the lock (C) and the measured contact-direction mix will
  decide whether a flat path is worth it. The 4-instruction table lookup needs a known direction,
  so it is a lock, not a general check.
- S3 accept: no bookkeeping on the front path. B's sensing moves to the slow path and uses only
  stateless data (neighbour energies, POP counts).
- S4 accept for B: scouts/nuclei in the opener; promote to the kernel if the simulator shows a gain.
- S5 accept for kernel: during the grab, cells with e>=10 feed a friend that has an empty outward
  neighbour (test the threshold in the simulator).
- S6 accept: drop walking raiders; keep opportunistic bites on cells with <=2.
- S7 partial: the lock wins outright only against slower code (it does vs every bot); add a
  periodic tick-masked unlock.
- S8 accept: refill a freed square as fast as the eat path (post table EMPTY -> SPLIT+d for C);
  bite order = kill (<=2) first, then a consistent direction order.
- S9 partial: capped donors (e>=49) feed the poorest friend with e <= donor-3 (no back-and-forth);
  other donors margin 4 and keep e>=10 after feeding. Tune in the simulator.
- S10 partial: keep three designs, but give them one shared fast kernel and distinct bets:
  A = kernel only (economy, simplest), B = expansion bet (scouts, feed-assisted grab, slow-path push),
  C = initiative bet (lock/post, fast refill, salient push). Features that win in the simulator move
  into the kernel. Reject Lattice and Turtle.
- S11 accept: effort order = front path, then grab speed, then logistics and push rules.
- S12 accept: gap rule: fill the gap row only with a child of >=8, by feeding the parent first.
- S13 partial: no tick-0 init on the hot path; the home corner is computed on the slow path only
  (from VIEW_COLONY if the colony-to-corner mapping is fixed, else stored in memory once).
- S14 done: hunter.asm read (see bot facts).
- S15 accept: merged into 1.3.

## Asm review (X)
- X1 accept: kernel front path "F6" = `movdqu` (VIEW_CELLS+7) / `pcmpeqb` vs an aligned constant with 2 in
  lanes 0,4,6,10 and 0xFF elsewhere / `pmovmskb` / `jmp [fight_tbl+rax*8]` -> `mov al,ACT_EAT+d` / `ret`
  = 6 flat in every direction (beats Hunter's 7-16 everywhere); a miss costs 4 and lands in the slow path.
- X2 accept: every SSE memory constant `align 16`; unaligned windows use `movdqu`. First harness test.
- X3 accept: no home byte, no init; zero memory = default. Corner from VIEW_COLONY tables if the
  slot-to-corner mapping is fixed (verify), else from x/y on the slow path.
- X4 accept, and it reshapes C: a checked lock gains only 1 over F6, and the 3-instruction blind lock has
  no cheap safe exit (any exit test brings it to 5). C becomes the "lock" bet with a checked 5-instruction
  lock and +3 on other paths; ship only if measured opponent eat paths are at or below 6.
- X5 accept: no mode dispatch on the hot path; role dispatch only on the slow path.
- X6 accept: every table entry filled (unreachable -> `xor eax,eax`/`ret`); tables generated by Python and
  the source flattened with `nasm -e` (the server rejects %include).
- X7 accept: drop "front friends first" feed priority; "poorest friend" already routes energy to the front.
- X8 accept: B's strength estimate costs 18-24 (slow path only): total - 2 x enemy energy via `psadbw`.
- X9 accept: drop energy-delta initiative sensing from v1.
- X10 accept: SSE2/SSE3 only; `bsf` with a zero check; enemy tests only via `pcmpeqb` (wall=3 shares bit 1).
- X11 partial: raiders are dropped (S6), but the 25-bit enemy-mask technique is kept for B's scouts and
  push rule. Accept the safety rule: clear any lock byte before a split so children never inherit it.
- X12 accept: no Unicorn in the match loop.
- X13 accept: test plan = (1) differential-test each asm cell against its Python reference over all
  neighbour/energy/memory combinations in Unicorn, (2) strategy runs with Python reference cells and
  validated path counts, (3) site sandbox for ground truth. Stage 1 simulator already fits this.
- X14 accept: calibrate counting on the site with known-length cells before trusting comparisons.
- X15 accept: one kernel source with `%ifdef DESIGN_A/B/C`, flattened per design.
