# Deep review: what the measures say, and the path forward (2026-11-13)

> Note: paths under `data/` name local working data that is not published in the repo (see architecture/data-pulls.md). Historical document.

Inputs: `docs/evidence/bane-v22-evidence-2026-11-12.md` (pack) and, in `data/evidence-2026-11-12/`: `m1-gate-summary.txt`,
`m2-varsi-budget.txt`, `m2b-far-none.txt`, `m3-losses-by-winner.txt`, `m5-refill-killer.txt`, `m7-newborns.txt`,
`m-r1-first-contact.txt`, `m-solo-matrix.txt`, `notes-2026-11-13.md`, `duel-summary.txt`. Source: `cells/bane2.asm`.
Real replays and solo runs only. Inferences are marked; every claim has a confidence.

## 1. Verdict

Build one bundle, v2.3, and upload it once:

- **A. Stored bite written in advance.** A cell that rests with an empty neighbour stores a bite on that square. An
  enemy that enters is then bitten in 4 instructions, not 16 (12 in v2.3a). Only rest paths get longer.
- **B. Opening "first child long 8/2, split toward the emptiest side"**, or a better variant if a short solo search
  finds one with no flag.
- **v2.3a** (first bite 12), already built and held.

Leave alone: the refill gate and prey-hold thresholds, the bite layout (no queue), feeding, the 6/2 opening, the
UP / DOWN beyond-square pattern.

Expected size, stated plainly: this is an incremental gain. It reaches the close equal-start games. It does not close
the large gaps, the bad starts, or Siect-F. No measured lever does. Confidence that the bundle flips at least 1 in 5
equal-start games against VarSi-type rivals: 40% (inferred).

## 2. What the data settled

| # | Question | Answer | Evidence | Conf. |
|---|---|---|---|---|
| 1 | Who beats Bane? | 25 losses in 313 single-cell games: VarSi 10, Colossus 8, CogSpore 5, CogBloomXT 2. Later: Siect-F 3 of 3 (4 of 4 with 131188). Against VarSi the result follows the start: good 3/3, equal 0/5, bad 0/3 | m3; pack s4 | 95% |
| 2 | What is a bad start? | A wall or corner square. Solo v2.2 reproduces the real window-a boxed shares exactly (19.4 / 43.2 / 23.2%) and reaches 741 cells at t60 against 1,446 on equal squares (-49%) | m-solo-matrix | 95% |
| 3 | Is the VarSi gap a growth-potential gap? | No (inferred). Far-cell failed splits are the same solo and real (18.4 / 18.6% in window b), and no rival beat our solo curve at t60 (pack s5). The shortfall is in cells near the enemy: near+front cells split 28.7% against VarSi 58.1% | m2b; m2 pooled rows; pack s5 | 70% |
| 4 | What is the near-cell idle time? | About 85% is the prey hold (938 of 1,094 cell-ticks, 5 games, window b) | m2, none by rule | 90% |
| 5 | What does a hold cost? | A hold from 5-7 energy ends lost 60%, from 8-11 32-39%. In the 5 equal-start losses: 29 lost squares per game in window b (11 from 8-11 holds). Net contested squares: -64 per game by t100; two of the five t100 gaps are -154 and -188 | m1 delay view, pooled tables; pack s8 | 85% |
| 6 | Would a lower gate help? | Not shown. No Bane fill matches the hold situation. VarSi's own 5-7 fills there keep the square 41-71% and lose the parent 20-37% | m1 fills by enemy at s | 75% |
| 7 | Where is the first-bite loss? | When an enemy enters beside our idle cell, it bites first 47.4% (holder) or 64.8% (cell under 5 energy). A killer whose stored bite already points at the square is bitten first 2.0% | m-r1 (2); m5 nb=0 | 85% |
| 8 | Does the stored-bite path need work? | No. With no other enemy beside it, the killer bites the refill child 97.3% (rivals 94-100%). The 31.5% in pack s14 is killers busy with another enemy (73% of cases) | m5 | 90% |
| 9 | Do newborns need a stored bite? | It decides their first race: 86.6% won with a valid inherited bite, 19.1% with a scan. But gate children already have one in most cases outside Siect-F games (Yen: 4,344 valid against 132 none) | m7; m-r1 (3) | 85% |
| 10 | Colossus? | Same constant handicap in wins and losses (window-b split share 5.0 / 7.1 lost, 4.7 / 6.2 and 5.5 / 6.6 won). No separate mechanism; starts decide | m2 Colossus mode; notes | 70% |
| 11 | Siect-F? | Fast bites from the first tick of contact: holder against Siect-F 7.2 / 92.8; even a valid stored bite wins only 11.8%. (Inferred, 65%: a blind bite queue copied to children, so newborns and leftover bites hit in 3.) Nothing above touches it | m-r1 (2), (3); pack s12 | 85% |

Corrections to the pack: split parents were guessed, now matched by energy (s8, s9b superseded; s7 shifted little). "Far
split rates are equal" was an artefact of that guess. Finding 1 (UP / DOWN beyond-square) is at most 2.2% of lost
squares (m1, rule4 columns): dropped. Finding 2: the hold and the gate are one boundary.

## 3. The path

### Step 1. Stored bite written in advance (A)

- **Where.** Every path that ends in a rest with an empty neighbour: the prey hold, the settled rest below 5 energy,
  the blocked walker below 5. Not the boxed or feed paths, which also reach `rest:`.
- **What.** When gate 1 sees a refill pattern (an empty neighbour with an enemy beside or beyond it), store a bite on
  gate 1's first-choice square. With no refill pattern, write nothing, so a killer keeps its bite on the square it
  emptied. 74% of enemy entries beside a holder go into the first-choice square (m-r1 2b).
- **Two traps (corrected 2026-11-13).** Do not test the stored square for "empty": CELL_EMPTY is 0 and so is "no
  stored bite", and an inherited bite can point at any empty square, which would block the write for good. Take the
  square from the gate table, not from `al`: at `rest:` `al` is 0 on the boxed path and a feed action on the feed path.
- **Cost.** None on any racing path: stored bite 4, first bite 12, refill 16, split 16, walker move 39 do not change.
  A rest races nothing. Confidence 95% (source reading).
- **Gain.** About 190 such contacts per game (holder or thin rester, no other enemy; 5,069 entries over the 27 Bane
  v2.2 games). First-order flips with the coverage count: 9.4% of holder contacts and 21.7% of thin-rester contacts,
  about 25 first bites per game (corrected 2026-11-13: first written over 81 replays as about 45 and about 12). The measured armed case (row 7)
  suggests up to twice that (inferred). Works against every rival whose bite costs 4 or more. Confidence it helps: 85%.
- **Tests** (each shown failing first on v2.3a):
  - unit, scripted enemy: an enemy enters the first-choice square of a holder; Bane's bite is logged at 4 instructions.
  - unit: a killer whose emptied square is the only refill square keeps its stored bite there.
  - unit: a cell with no stored bite (byte 0) and a refill pattern stores one; a cell whose inherited bite points at
    an empty square that is not a refill square stores one too.
  - unit: boxed and feed paths store nothing.
  - integration, solo: runs from the 11 sampled squares are identical to v2.3a at every tick (cells and energy).
  - `check_cells`: path counts as listed above.

### Step 2. Opening (B)

- **Default:** "first child long 8/2, emptiest side". It is never below v2.2 at any of the 11 squares or any tick; t60
  +5.2% (equal), +7.7% (bad), +4.5% (good); window-a boxing 11.8 -> 10.1% (m-solo-matrix).
- **Short solo search first:** variants around "16/2, stop after 4 steps with no friend in view". That one gives +21.6%
  at t40 and +10.2% at t60 on equal squares, but is -30% at t20 on two corner squares and -0.7 to -4.8% at t100 on
  three. Accept a variant only with no flag from t20 to t60 on all 11 squares and at most -1% at t100.
- **Then the real cell:** it must match the sketch within 1% at t30 and t60 on the 11 squares; report new path counts.
- Confidence the solo gain carries into real games: 60% (solo evidence only).

### Step 3. One upload, then measure (needs the user's approval)

A new version restarts the rating, so judge by measures, not rating, on the first 25 replays:

| Measure (script) | v2.2 | Target |
|---|---|---|
| Enemy bites first when it enters beside a holder (`first_contact.py`) | 47.4% | 30% or less |
| Same, beside a rester under 5 energy | 64.8% | 40% or less |
| Holds from 5-7 energy that end lost (`gate_split.py`) | 60% | under 50% |
| Window-a boxed share, equal squares (`budget.py`) | 11.8% | the solo value of the chosen opening |
| Siect-F | 0 of 4 | no change expected |

Update the marker costs in `order.py`, `race.py`, `duel.py` by match id first.

### Step 4. Decide the hold with v2.3 data

If armed holders still lose half of the 5-7 holds, test a lower gate whose child gets a stored bite toward the enemy.
The evidence for that child: thin children with a valid stored bite are dead within 10 ticks 9.9% of the time, against
66.7% without (m-r1 3; Yen 22.7% against 71.5%). That is a different situation from a hold, so it needs its own data.

### Track B. Siect-F (design study, no build)

- Facts: it is armed on 60.7% of pair-ticks; our armed cells win 82.4%, but we are armed on 1.3% (duel-summary). Its
  one slow moment is after it rests: then our refill child bit it first 27.5% (m5).
- First measure, existing replays: refill delay after a Siect-F kill (0, 1, 2, 3+ ticks) against "child bitten on its
  first tick". If a delay of 2 or more cuts it sharply, a delayed refill is a candidate that needs no faster bite.
- The structural answer is a 3-instruction bite. That is a new cell, not a Bane patch (first report: the queue taxes
  every other path). Decide after the measure.

## 4. What not to build now

| Candidate | Why not | Evidence |
|---|---|---|
| Gate 12 -> 8 | At most 11 squares per game in window b | m1 episodes |
| Gate 12 -> 5 | Thin children: 62.5% bitten on the first tick, 39.4% alive after 10 | m1 fills |
| Stored bite written by the refill split | Gate children already carry a valid one outside Siect-F games | m-r1 (3) |
| Opening 6/2 | 13-37% behind at t30 | m-solo-starts |
| Blind bite queue in Bane | Unchanged from the first report | pack s15, s16 |
| Far-cell collision fix | Already inside the solo curve; costs energy, not squares, once growth is front-limited (inferred) | m2b |

## 5. Risks

1. The opening's solo gain does not carry over. Warning sign: real t30 below v2.2's on equal squares.
2. The stored bite points at the wrong square (26% of entries). Warning sign: holder target missed while thin-rester
   target met.
3. Two changes in one upload. They show in different tables (first contact against growth), so they can be told apart.
4. Siect-F's share of games grows (4 of Bane's last 50). Then Track B becomes the main work.

## 6. Decisions for the user

1. Build A now and bundle B into the same upload (recommended), or upload A first and B later (two rating restarts).
2. Run the Siect-F refill-delay measure now.
3. Sandbox games against ladder cells: settled, no (the standing rule against games with rivals). v2.3 is judged by
   the replay measures after the upload.
