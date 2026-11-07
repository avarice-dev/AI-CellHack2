"""Shared helpers for the engine tests: scripted policies on tiny hand-built boards."""

import os
import sys

SIM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SIM_DIR not in sys.path:
    sys.path.insert(0, SIM_DIR)

import engine as E  # noqa: E402

NOP = (E.ACT_NOP, 1)


def script(table, default=NOP):
    """Policy that looks up its action by (tick, x, y), then (x, y), else default.

    Values are (action, insn_count).  Keys use the cell's position at decide time.
    """
    def pol(view, mem):
        r = table.get((view.tick, view.x, view.y))
        if r is None:
            r = table.get((view.x, view.y), default)
        return r
    return pol


def board(policies, w=5, h=5, seed=0, **kw):
    """Empty board with no start cells; place cells with eng.add_cell."""
    return E.Engine(policies, width=w, height=h, seed=seed, place_start=False, **kw)


def energy_at(eng, x, y):
    i = eng.cell_at(x, y)
    return None if i is None else eng.c_en[i]


def move(d):
    return E.ACT_MOVE + d


def split(d):
    return E.ACT_SPLIT + d


def eat(d):
    return E.ACT_EAT + d


def feed(d):
    return E.ACT_FEED + d


UP, RIGHT, DOWN, LEFT = E.DIR_UP, E.DIR_RIGHT, E.DIR_DOWN, E.DIR_LEFT
REST = E.ACT_REST
