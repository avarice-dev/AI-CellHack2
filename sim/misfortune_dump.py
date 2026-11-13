"""Misfortune build-review tables (briefs/misfortune-build-review-2026-11-13.md), from sim/cells_ref.make_misfortune.

  python misfortune_dump.py paths     # path table: action and count per path, Misfortune variants vs Bane v2.3a
  python misfortune_dump.py dumps     # memory bytes 0-63 after arming at the review's e0 values, and after the next
                                      # slow tick, every direction, cap and exact flag (exact 1 at te 5 and te 9)
"""

import sys

import cells_ref as C
import engine as E

EM, FR, EN, WA = E.CELL_EMPTY, E.CELL_FRIEND, E.CELL_ENEMY, E.CELL_WALL
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
IDX = E.VIEW_DIR
DIRS = 'URDL'
DUMP_E0 = (1, 2, 5, 12, 39, 40, 46, 47, 48, 49, 50)


class View(object):
    def __init__(self, energy, adj=(EM, EM, EM, EM), tick=100, x=30, y=31):
        self.cells = [EM] * 25
        self.cells[12] = FR
        self.energies = [0] * 25
        self.energies[12] = energy
        for i, t in zip(IDX, adj):
            self.cells[i] = t
            self.energies[i] = 20 if t in (FR, EN) else 0
        self.energy, self.tick, self.x, self.y, self.w, self.h = energy, tick, x, y, 64, 64


def mem(bear=0, steps=0, pos=None):
    m = bytearray(64)
    m[0], m[1] = bear, steps
    if pos is not None:
        m[4:8] = (pos[0] | pos[1] << 16).to_bytes(4, 'little')
    return m


def boxed_view(e, fe=20, rings=FR):
    v = View(e, (FR, FR, FR, FR))
    for i in range(25):
        if i != 12:
            v.cells[i] = rings if i not in IDX else FR
            v.energies[i] = fe
    return v


def cases():
    """(path name, view, memory factory) for each path."""
    here = (30, 31)
    out = []

    def armed():
        m = mem()
        m[C.MISFORTUNE_SLOT0 + 20] = E.ACT_EAT + RIGHT
        return m
    out.append(('armed bite (slot set)', View(20, (EM, EN, EM, EM)), armed))
    out.append(('first bite (scan, arming)', View(20, (EM, EN, EM, EM)), mem))
    v = View(12, (FR, FR, EM, FR))
    v.cells[16] = EN
    out.append(('refill (gate 1, freed square)', v, mem))
    out.append(('gate 1 split (e >= 16, no enemy)', View(20), mem))
    out.append(('walker move', View(8, (FR, EM, FR, FR)), lambda: mem(bear=RIGHT, steps=3, pos=(1, 2))))
    out.append(('walker blocked, settles and splits', View(8, (EM, FR, FR, FR)),
                lambda: mem(bear=RIGHT, steps=3, pos=(1, 2))))
    out.append(('settled split, first child forward', View(8), lambda: mem(bear=UP, steps=0, pos=(1, 2))))
    out.append(('settled split, rotate 1', View(8, (FR, EM, FR, FR)), lambda: mem(bear=UP, steps=0, pos=here)))
    out.append(('settled split, rotate 2', View(8, (FR, FR, EM, FR)), lambda: mem(bear=UP, steps=0, pos=here)))
    out.append(('settled split, rotate 3', View(8, (FR, FR, FR, EM)), lambda: mem(bear=UP, steps=0, pos=here)))
    out.append(('settled split, fourth square', View(8, (EM, FR, FR, FR)), lambda: mem(bear=UP, steps=0, pos=here)))
    v = View(8, (EM, EM, EM, EM))
    v.cells[6] = EN
    out.append(('prey hold (enemy on a diagonal)', v, mem))
    v = View(8, (EM, EM, EM, EM), tick=2990)
    v.cells[6] = EN
    out.append(('late split (tick >= 2980)', v, mem))
    v = View(3, (EM, EM, EM, EM))
    v.cells[6] = EN
    out.append(('threat rest (e < 5)', v, mem))
    out.append(('settled rest (e < 5)', View(3), mem))
    out.append(('boxed rest (e < 16)', boxed_view(10), mem))
    v = boxed_view(10)
    v.cells[2] = EM
    out.append(('boxed Schism feed (friend with an empty edge)', v, mem))
    out.append(('boxed Scourge feed (poorest friend)', boxed_view(30), mem))
    v = boxed_view(20)
    v.energies[IDX[UP]] = 48
    v.cells[2] = EM
    out.append(('boxed, edge friend 48 with an empty edge (A pull, B lift)', v, mem))
    v = boxed_view(20)
    v.energies[IDX[UP]] = 48
    v.cells[2] = EN
    out.append(('boxed, edge friend 48 with an enemy edge (B hold)', v, mem))
    out.append(('boxed interior, all friends at 50', boxed_view(50, fe=50), mem))
    return out


def act_name(a):
    if a == E.ACT_REST:
        return 'REST'
    return {E.ACT_MOVE: 'MOVE', E.ACT_SPLIT: 'SPLIT', E.ACT_EAT: 'EAT', E.ACT_FEED: 'FEED'}.get(a & 0xF0, '?') + \
        ' ' + DIRS[a & 3]


def path_table():
    pols = [('A1', C.make_misfortune(cap='A', exact=1)), ('B1', C.make_misfortune(cap='B', exact=1)),
            ('N1', C.make_misfortune(cap='N', exact=1)), ('B0', C.make_misfortune(cap='B', exact=0)),
            ('A0', C.make_misfortune(cap='A', exact=0)), ('v2.3a', C.make_bane3())]
    lines = ['| path | ' + ' | '.join(n for n, _ in pols) + ' |', '|---|' + '---|' * len(pols)]
    for name, v, mk in cases():
        cells = []
        for _, p in pols:
            a, n, t = p(v, mk())
            cells.append('%s %d' % (act_name(a), n))
        lines.append('| %s | %s |' % (name, ' | '.join(cells)))
    return '\n'.join(lines)


def hexdump(m):
    return ' '.join('%02x' % b for b in m)


def byte_dumps():
    out = ['# memory bytes 0-63 (hex). State before arming: [0] bearing 3, [1] steps 7, [4..7] position (30, 31).',
           '# "arm" = after the arming call (an enemy on the given side, energy te); "slow" = after the next call',
           '# at energy e (shown), a boxed all-friend view, no slot armed at e.  Byte 8 = e0; slot(e) = byte 13 + e.']
    for cap in 'ABN':
        for exact, tes in ((0, (20,)), (1, (5, 9))):
            p = C.make_misfortune(cap=cap, exact=exact)
            for te in tes:
                for e0 in DUMP_E0:
                    for d in range(4):
                        adj = [EM, EM, EM, EM]
                        adj[d] = EN
                        v = View(e0, tuple(adj))
                        v.energies[IDX[d]] = te
                        m = mem(bear=3, steps=7, pos=(30, 31))
                        p(v, m)
                        arm = bytes(m)
                        for e in (e0 + 1, e0 - 1, e0 + 3, e0 - 3):
                            if 1 <= e <= 50 and not m[C.MISFORTUNE_SLOT0 + e]:
                                break
                        p(boxed_view(e), m)
                        out.append('cap %s exact %d te %2d e0 %2d %s | arm  %s' % (cap, exact, te, e0, DIRS[d],
                                                                                 hexdump(arm)))
                        out.append('                         e %2d | slow %s' % (e, hexdump(m)))
    return '\n'.join(out)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'paths'
    print(path_table() if what == 'paths' else byte_dumps())
