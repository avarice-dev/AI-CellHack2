"""The five open bots, ported line by line from docs/bots/*.asm.

insn_count = every executed instruction on that path, including taken jumps and ret (the Reference:
"The engine counts every instruction").  Path counts were traced by hand from the asm; each comment
shows the instruction sequence that was counted.  `jb` is an unsigned compare; rsi is 0..50 so it
behaves like `<`.
"""

from engine import (ACT_REST, ACT_SPLIT, ACT_EAT, ACT_FEED, ACT_MOVE, ACT_DIR_MASK,
                    CELL_ENEMY, CELL_FRIEND, VIEW_UP, VIEW_RIGHT, VIEW_DOWN, VIEW_LEFT)

# ---- thresholds, exactly as in the asm ----
HUNTER_FAT = 6       # hunter.asm: cmp rsi, 6 / jb rest
MEDIC_RICH = 15      # medic.asm:  cmp rsi, 15 / jb grow
MEDIC_FAT = 6        # medic.asm:  cmp rsi, 6 / jb rest
RANDOM_MIN = 6       # random.asm: cmp rsi, 6 / jb rest
WALKER_FAT = 6       # walker.asm: cmp rsi, 6 / jb wander


def idle(view, mem):
    # mov al, ACT_REST / ret
    return ACT_REST, 2


def hunter(view, mem):
    c = view.cells
    # lea r8 (1); per direction: mov, cmp, je (3); taken je -> mov, add, ret (3)
    if c[VIEW_UP] == CELL_ENEMY:
        return ACT_EAT + 0, 7
    if c[VIEW_RIGHT] == CELL_ENEMY:
        return ACT_EAT + 1, 10
    if c[VIEW_DOWN] == CELL_ENEMY:
        return ACT_EAT + 2, 13
    if c[VIEW_LEFT] == CELL_ENEMY:
        return ACT_EAT + 3, 16
    # 13 so far; cmp, jb (2)
    if view.energy < HUNTER_FAT:
        return ACT_REST, 17                       # + mov, ret
    # mov cl, and cl, mov al, add al, ret (5); splits blindly in a random direction
    return ACT_SPLIT + (view.rand & ACT_DIR_MASK), 20


def medic(view, mem):
    e = view.energy
    # cmp, jb (2)
    if e >= MEDIC_RICH:
        # lea, mov, cmp, jne (4)
        if view.cells[VIEW_UP] == CELL_FRIEND:
            return ACT_FEED + 0, 9                # + mov, add, ret
        base = 6
    else:
        base = 2
    # grow: cmp, jb (2)
    if e < MEDIC_FAT:
        return ACT_REST, base + 4                 # + mov, ret  -> 6
    return ACT_SPLIT + (view.rand & ACT_DIR_MASK), base + 7   # + mov, and, mov, add, ret -> 9 / 13


def random_bot(view, mem):
    # cmp, jb (2)
    if view.energy < RANDOM_MIN:
        return ACT_REST, 4                        # + mov, ret
    r = view.rand
    # mov, and, shr, mov, and, and, add, shl, and, mov, add, ret (12)
    act = ((((r & 0xF0) >> 4) & 3) + 1) << 4     # 0x10 MOVE, 0x20 SPLIT, 0x30 EAT, 0x40 FEED
    return act + ((r & 0x0F) & ACT_DIR_MASK), 14


def walker(view, mem):
    r = view.rand
    # cmp, jb (2)
    if view.energy >= WALKER_FAT:
        return ACT_SPLIT + (r & ACT_DIR_MASK), 7  # + mov, and, mov, add, ret
    # wander: mov, test, jz (3)
    if not (r & 0x80):
        return ACT_REST, 7                        # + mov, ret
    return ACT_MOVE + (r & ACT_DIR_MASK), 9       # + and, mov, add, ret


BOTS = {
    'hunter': hunter,
    'idle': idle,
    'medic': medic,
    'random': random_bot,
    'walker': walker,
}
