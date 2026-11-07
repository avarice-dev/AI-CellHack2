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

## Round 2 review (reviewer: Claude, F) — decisions 2026-11-07
Review: `r2-review.md`. Lead checks before deciding: arithmetic in its sections 1.1-1.4 re-traced and correct,
with two corrections. (1) Its 1.5 says a blind lock is 2 without taken jumps; wrong, the locked path's `jz` is
NOT taken, so the blind lock is 3 under both conventions (it still beats everything). (2) Post lock: the
unlocked table entry must be (-VIEW_W)&0xFF so `add al` gives 0, and since VIEW_W differs on sandbox boards,
every index 8k (k = 4..255) must hold (-k)&0xFF; locked indices are odd, so no collisions (2041-byte table).
The post lock also splits blindly on EMPTY: at e<5 the tick is wasted (no rest), at e=5-6 the child is 2-3.
Its simulator runs are simplified (Python policies, naive feeders) and are treated as indications, not facts.

- F1 accept: the lock moves into the kernel; slot C as "the lock bet" is dissolved. Variant = post lock
  (5 locked, refill at 5), checked lock kept as fallback if E3 shows blind EMPTY-splits cost more than the
  refill race gains. Unlocked tax is +4 (first contact 11). Conditional on F6/F11 calibration.
- F2 accept: multi-enemy choice encoded in the fight table at 6 (two enemies: fixed D,L,U,R order; three:
  opposite the friend side; four: any). Kill-first dropped from v1; E4 confirms.
- F3 accept: fed or tied fronts freeze; feeding is first-order defence. Effort order revised: (1) front path
  and feeding defence, (2) grab incl. scouts, (3) refill and push. Rewrite designs.md 1.1.4 and 1.4.
- F4 accept: scouts become a kernel feature with count/bearings as parameters (count 0 allowed); E2 sets them.
  Note the review's own data: a naive feed-assist gave ~2% (290 vs 284 cells at tick 100); assist stays in
  the kernel only if E2 shows a real gain with a better design (fat-burst tips).
- F5 partial: adopt the structure (one kernel, three parameter settings, no pure-control slot); names Hold /
  Spore / Breach adopted as working names. Final slot specs only after E9; A remains the simulator baseline.
- F6 accept: counting convention is the first sandbox calibration (three cells: `mov al,1/ret`,
  `jmp x / x: mov al,1 / ret`, and one `rep` cell). Without taken jumps F6 = 5 and the post/checked lock = 5.
- F7 accept as rival, defer as ours: R-Blind3 joins the rival set (needs rax = 0 at entry, verify). A blind-3
  variant of Breach is considered only after E6 and real rival averages.
- F8 accept in principle, needs the user: a Sprint cell on the ladder means writing cell code and publishing
  under the user's account (both need the user's go-ahead). Asked 2026-11-07.
- F9 accept: refill race is the second initiative number; covered by the post lock and E3.
- F10 partial: direction accepted (second row feeds the front, producers kept below the cap, no feed from
  <=4, front cell never <=2); thresholds (12 / 48) are E1 parameters, not decisions.
- F11 accept: "memory writes persist when stunned" is the top sandbox fact for the lock; sim keeps it as a
  flag-able assumption (add a switch).
- F12 accept: reverses X11's "clear the lock byte before a split". With a self-checking lock the inherited
  byte is harmless; with the post lock it is the breach-column mechanism.
- F13 accept: generate tables with `times` runs, check flattened source < 64 KB, no `org` in our source,
  write `[abs fight_tbl+rax*8]` and check the listing.
- F14 accept: sentinel = VIEW_W (documented field, never 0..3 on a real board) instead of unused byte 100;
  check ABI_VERSION = 4 at build time (`%if`).
- F15 accept (= E1 frozen front with brigade variants).
- F16 accept (= E2 scouts/grab, incl. a dead-quadrant slot with Idle).
- F17 accept (= E3 refill race and E4 multi-enemy cost).
- F18 accept: rival set E0 is the next simulator task (R-F6, R-Post5, R-Blind3, R-Feeder, R-Grab, R-Static,
  R-Hunter+), each with a no-taken-jumps count; E5 reruns E1/E3 with the flipped convention.
- F19 accept: slow path orders feed shorter than split. Sim already sizes the child at the parent's turn
  (live energy); add to the sandbox list.
- F20 accept as E8 starting values: stop long-range feed 2950, fill from 2980, last-tick children near an
  enemy only if >= 3.
