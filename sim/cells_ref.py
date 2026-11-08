"""Python reference policies for our own asm cells (cells/*.asm).

sprint(view, mem) mirrors cells/sprint.asm decision for decision and returns
(action, insn, insn_no_taken_jumps) with the exact path counts of the asm (every executed instruction,
including taken jumps and ret; the third value leaves taken jumps out, the indirect `jmp [table]`
counting as a taken jump).  Written independently of cells/gen_sprint.py's tables so the two can be
checked against each other (sim/tests/test_cells_ref.py).
"""

from engine import ACT_REST, ACT_SPLIT, ACT_EAT, CELL_ENEMY, CELL_EMPTY, VIEW_DIR, VIEW_CENTER

DOWN, LEFT, UP, RIGHT = 2, 3, 0, 1
SPRINT_FIGHT_PRIO = (DOWN, LEFT, UP, RIGHT)
SPRINT_SPLIT_PRIO = (DOWN, RIGHT, UP, LEFT)
SPRINT_SPLIT_MIN = 5
SPRINT_THREAT_MIN = 16
SPRINT_LATE_TICK = 2980


def _sprint_bite(enemies):
    if len(enemies) == 3:
        free = [d for d in range(4) if d not in enemies][0]
        return (free + 2) & 3                 # opposite of the one non-enemy side
    for d in SPRINT_FIGHT_PRIO:
        if d in enemies:
            return d


def _sprint_split(c):
    for d in SPRINT_SPLIT_PRIO:
        if c[VIEW_DIR[d]] == CELL_EMPTY:
            return ACT_SPLIT + d
    return ACT_REST                            # split_tbl mask 0


def sprint(view, mem):
    c = view.cells
    enemies = [d for d in range(4) if c[VIEW_DIR[d]] == CELL_ENEMY]
    # movdqu, pcmpeqb, pmovmskb, jmp [tbl] (4) -> mov, ret
    if enemies:
        return ACT_EAT + _sprint_bite(enemies), 6, 5
    e = view.energy
    # slow: cmp, jb (6 so far)
    if e < SPRINT_SPLIT_MIN:
        return ACT_REST, 8, 6                  # jb taken -> mov, ret
    # movdqu x2, pcmpeqb x2, por, pmovmskb, test, jnz (14 so far)
    seen = any(c[i] == CELL_ENEMY for i in range(25) if i != VIEW_CENTER)
    if not seen:
        return _sprint_split(c), 19, 18        # fall into split: movdqu, pcmpeqb, pmovmskb, mov, ret
    # threat (jnz taken): cmp, jae
    if e >= SPRINT_THREAT_MIN:
        return _sprint_split(c), 21, 18
    # cmp dword tick, jae
    if view.tick >= SPRINT_LATE_TICK:
        return _sprint_split(c), 23, 20
    return ACT_REST, 20, 18                    # fall into rest: mov, ret
