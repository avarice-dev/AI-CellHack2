# Review r1 - rules accuracy and exploits (designs.md sections 1-2, plus rule-dependent claims in 3-5)

> **Update 2026-11-08 (docs re-review).** This is a historical record; its open questions are kept as written. A later full re-read of `docs/` settled several of them: every instruction counts, including taken jumps and `ret` (Reference p.3); energy is capped at 50 in the Tidy step (Rules p.1); feed gives 2 of the feeder's energy to any cell in that direction, so "fed +3" is feed 2 + rest 1, with no bonus (Rules p.1-2); a square freed by a death opens next tick, one freed by a move opens the same tick (Rules p.2); matches are deterministic from the seed (Rules p.3); SSE2 and SSE3 are available (Reference p.3); loops, the stack and `[rdx]` memory are allowed by the game. Ladder starts are not corners (replays; the Rules never say corners). See `architecture/overview.md` for the current summary.

Sources: Rules, Quick start, Reference PDFs, cellhack.inc. Quotes are verbatim.

## A. Claims checked against the docs

| # | Draft claim | Verdict | Doc text |
|---|---|---|---|
| 1.1.1 | Score = population; energy and instructions are tie-breaks | OK, but ladder scoring is placement | "rank by population, then total energy, then fewer instructions run over the whole match"; "award 3, 2, 1 and 0 points by placement" |
| 1.1.2 | Splitting does not destroy energy; growth not limited by energy | OVERSTATED | Quick start: "Nothing costs energy except feeding and splitting." Rules: "new cell there with half your energy". Rounding unspecified. Energy is the throttle on growth (B1) |
| 1.1.3 | "Rest (+1) is the only income" | WRONG | Rules "Worth knowing" says resting is the only income, but step 4 says EAT "adds it to yours". Eating enemy or friend is +2 income: "You can eat and feed your own cells." |
| 1.1.4 | Initiative = fewest instructions; bite stuns a target that has not acted; ties random | OK | "Cells take their turns in order of how many instructions their decision ran, fewest first"; "if it has not had its turn yet, it loses its action"; "Equal instruction counts are ordered at random" |
| 1.1.5 | "A friend can feed at most 2/tick" | AMBIGUOUS | Each feeder gives 2; a cell with 3 friend neighbours can receive 6 (up to 8) per tick. "A cell eaten by several others loses energy to each in turn" |
| 1.1.5 | Chain of feeders has no income | Mostly OK | A chain member that eats gets +2 |
| 1.1.6 | "child from a split at 5 has 2-3" so don't split next to an enemy | INCOMPLETE | The parent is left with the other half (2-3) too. Both are one-bite kills |
| 1.1.7 | Death square unusable until next tick; vacated square usable same tick; bite hits newcomer | OK | "A square vacated earlier in the tick can be entered later in the same tick; a square freed by a death cannot until the next tick." "a bite at a square someone stepped into hits the newcomer" |
| 1.1.8 | 64 bytes inherited at birth | OK, details missing | "a copy of the parent's memory"; "Newborns act from the next tick, with VIEW_AGE 0" |
| 1.1.9 | Free global info | OK, incomplete | Also VIEW_AGE, VIEW_RAND, ENERGIES of all 24 neighbours. POP_ENEMY is the sum over 3 colonies, so enemies cannot be told apart |
| 1.1.11 | Ladder includes the open bots | STATED AS FACT | Quick start only says "These play on the ladder from day one as players." Matchmaking mix is unknown |
| 1.1.12 | Faults | OK | "crashes, runs more than 1000 instructions, returns an unknown action" -> "does nothing that tick". Valid values: 0x00, 0x01, 0x10-13, 0x20-23, 0x30-33, 0x40-43 only |
| 1.1.13 | Cells cannot read each other's memory | OK | only `[rdx]` is exposed; energy and type are visible |
| 1.2 | SSE2 mask, `and 0x451` | OK | bits 0,4,6,10 = 0x451. 16-byte `movdqu` from VIEW_CELLS+7 is inside the 128-byte struct. Window also covers idx 10, 14, 22 (left/right/down at distance 2) but not up at distance 2 |
| 1.3 | "Do ret and taken jumps count?" | MOSTLY SETTLED | Reference: "The engine counts every instruction." Only `rep` granularity is open |
| 1.3 | "True corners or inset?" | MOSTLY SETTLED | cellhack.inc: "MAX_COLONIES equ 4 ; one per corner" |
| 2 | "END comes from a constant (3000)" | WRONG | cellhack.inc has no tick-limit constant. 3000 must be hard-coded; the docs say "After 3000 ticks" only in Quick start, not specifically for the ladder |
| 2 | Last two ticks: "a child that dies after the final count still counted" | WRONG/UNCLEAR | A newborn can be eaten in the tick it is born by any slower cell (newborns only "act from the next tick"). Whether the final count follows the last Tidy is not stated |
| 2 | Feed margin >= 4 | OK | follows from FEED_AMOUNT 2: difference d becomes d-4 |
| 5.3 | Raiders "forgo rest income"; "after a kill, split into the freed square" | WRONG x2 | Eating pays +2. The victim's square is held by the dead cell until Tidy, so a same-tick split fails; and the victim only dies if it had <= 2 |

## B. Rule details missed that change designs

B1. Growth is energy-throttled. Total colony energy only rises by REST (+1 per resting cell) and EAT. A split at 5 leaves 2-3 in each half, and each half needs 2-3 more rests before splitting again, so a frontier cell doubles about every 3-4 ticks. Land-grab front speed is set by how fast energy reaches border cells: a border cell with e >= 10 can split on consecutive ticks. So in the opening, interior energy should flow outward early, and "fat parent, fat child" matters early, not only late. "Not by an energy cost" should read "not by a fee, but by the energy supply".

B2. EAT is income and a stun. Eating gives +min(2, target energy). A duel winner nets +2/tick while the loser loses 2 and its action. "2 out vs 1 in" is true only for the loser. Eating a friend is a PULL of 2/tick and stuns that friend if it has not acted. Push (FEED) is better for idle capped interior cells; pull only if the puller is otherwise idle.

B3. Stun needs only ONE faster adjacent cell. Enemy A touching k of our cells acts before all k with probability 1/(k+1) when path costs are equal (random shuffle); if any one of ours acts before A and bites, A loses its whole action. A salient is therefore very bad for the side with the salient cell if numbers are equal, and a flat front is not safer.

B4. Path cost differs by direction. In the static-order check, enemy-up costs 4 and enemy-left costs 10. Our own cells have different initiative depending on where the enemy is. Equalize (SSE flat path) or deliberately put the cheap direction where it matters.

B5. Decisions use a start-of-tick snapshot; actions run later on the live board ("Targets are whatever is in that square when your turn comes"). Being late never gives information, only exposes you to bites. A split or move into a square another cell took first = "Nothing happens"; the tick is lost (no rest income either). In the opening, frontier cells sharing an empty neighbour collide. Break symmetry with a position/tick rule (e.g. only cells with (x+y+tick)&1 == 0 take contested squares) or VIEW_RAND.

B6. Cap timing. Energy is clamped only at Tidy, so a cell can exceed 50 within a tick; the excess is lost. Never REST at 50; EAT at 50 gives no income (still stuns/drains, which is denial); never FEED a target >= 49. The draft's "feed when e=50" is right only for targets <= 48. Whether a split uses live energy (52 -> 26/26) is open.

B7. Death and feeding order. "A cell that reaches 0 dies on the spot. It takes no turn, nobody can eat or feed it." A feeder saves a front cell only if it acts BEFORE the biter, or the front cell survives the bite. The draft puts feed at priority 4 after a long chain (15+ instructions) against enemy bites at 5-10. Keep front cells >= 5 so one bite never kills; give the feed path a short route when a friend neighbour has e <= 4 and an enemy is adjacent to it.

B8. A feeder with < 2 energy "gives all it has, and dies if that was all of it". Never feed from e <= 2. Feeding an enemy is legal (no stun).

B9. Memory inheritance specifics. The child's memory equals the parent's; the parent cannot give the child different bytes in the same tick. The child differentiates itself with VIEW_AGE == 0 (free "newborn" flag, no `flags` byte needed) plus fields the parent wrote in the splitting call (e.g. [last split dir]; child knows the parent is in the opposite direction). A stunned cell's call already ran, so its memory writes (probably) happened: "last action" in memory is the INTENDED action, not the executed one.

B10. Scoring is placement. 3/2/1/0 by rank; margin does not matter. "Dead colonies rank below them [living] by how long they lasted." The match ends early if one colony is left. A failed raid costs rank only if it changes ordering; the objective is to beat as many opponents as possible, not to maximize population. Elimination is the only way to rank below a living bot.

B11. CPU: "plain qemu64: SSE2 and SSE3 are available; anything newer is not guaranteed". Avoid pshufb (SSSE3), pblendvb/pmovzx (SSE4), popcnt, lzcnt, tzcnt (executes as bsf on old CPUs). Legacy-SSE memory operands (pcmpeqb xmm, [mem]) need 16-byte alignment: `align 16` before the constant; `movdqu` is unaligned-safe.

B12. "Registers, flags and the stack are reset before every call." If rax is zero at entry, `or al,[rdx]` sets flags for free (C1).

## C. Exploits and edge cases within the rules

C1. 3-instruction lock. Store the whole action byte (ACT_EAT+d) in `[rdx]`, 0 = no lock. If rax = 0 at entry: `or al,[rdx]` / `jz full_logic` / `ret` = 3 instructions on the lock path, versus 4 for movzx+jmp+mov+ret, with no jump table and only +2 (`or`, `jz`) on all other paths. Without rax = 0: `mov al,[rdx]` / `test al,al` / `jz` / `ret` = 4, still cheaper off the lock path. Unlock must happen on the full path, so the lock path needs no counter; combine with the 6-instruction checked variant for cells where the blind bite is dangerous.

C2. Colony-wide sync from VIEW_TICK and (x,y). All cells run the same code, so any function of tick/position is a free, perfectly coordinated schedule: checkerboard turn-taking against split/move collisions, feed waves that avoid ping-pong, timed pushes, endgame fill ordering.

C3. Move is free (only feeding and splitting cost). A fat cell can carry energy to the front by walking, 1 square/tick, versus 2 energy/tick per hop by feeding. "Two cells cannot swap places" but a square vacated earlier in the tick can be re-entered, so a few deliberate holes inside the colony act as a conveyor for fat cells. This is the best argument to revive the Lattice alternative in reduced form (few holes, not 20%).

C4. A same-tick conveyor needs order. A column advancing into vacated squares works only if the lead cell acts first; with identical code the order is random and the column jams. Make the lead cell's path shorter (it sees an empty square ahead).

C5. Dodge. A faster cell that MOVEs away makes a slower biter's EAT hit "nothing" and wastes the biter's tick. Niche, but useful for a cell that is about to lose a duel and is faster than the biter's mates.

C6. Stun denial. A fast biter on an enemy border cell also denies that cell's split and move. Biting every border enemy every tick freezes the enemy's expansion, not just drains it.

C7. Dead-square race. A cell that dies keeps its square until Tidy and cannot be fed, eaten or entered. After a kill the next-tick split into that square competes with enemy fill; the side with the shorter path wins it. Needs a cheap "split into square d" path.

C8. Ties between colonies go to the lower colony number (the last tie-break; irrelevant except in pathological equal boards).

C9. Matches are deterministic ("a match replays identically every time"; VIEW_RAND from the match seed), so a sandbox run vs Hunter is bit-for-bit reproducible for A/B tests of one change.

## D. Additions to the "verify in sandbox" list (1.3)

- Odd energy split: which side keeps the extra, and is total energy conserved (5 -> 2+3 or 2+2)?
- Does the child's memory copy include writes made in the same call as the split?
- Do a stunned cell's memory writes persist? Does a faulting call's memory persist? How is a faulted call ordered?
- Is split energy computed from live energy (after earlier feeds) rather than the snapshot rsi?
- Is VIEW_POP_SELF/ENEMY a start-of-tick snapshot? Does it include newborns?
- Last VIEW_TICK value (2999?), and is the final population counted after the last Tidy (does a last-tick split count)?
- Value of rax, other GPRs, xmm registers and DF at entry (rax = 0 enables C1).
- Does `rep` count per iteration or once? Do `ret` and not-taken `jz` count (docs say every instruction)?
- Does VIEW_CELLS[12] (self) report FRIEND, and VIEW_ENERGIES[12] equal rsi?
- Does EAT on a friend stun it? Is the excess lost when feeding a target at >= 49?
- Colony slot to corner mapping, starting squares, and the bot mix in ladder matches.
- Real ladder tick limit (3000 is stated only in Quick start) and whether the sandbox uses the same.
- Does `pcmpeqb xmm, [code]` with an unaligned address fault?
- Use the match page's per-call instruction average/max to measure the bots' real path costs; "initiative vs Hunter" depends on Hunter's actual count.
