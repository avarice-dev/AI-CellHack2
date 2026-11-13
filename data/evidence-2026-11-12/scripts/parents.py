"""Shared split-parent matcher for the evidence scripts (review 2026-11-12: one helper, so scripts cannot drift).

Replays log a birth (child id, colony, square, child energy) but not the parent.  The engine (sim/engine.py) applies
actions in turn order: eat takes min(2, target energy), feed gives min(2, feeder energy), a split gives the child
floor(e / 2) and the parent keeps the rest; no cap mid-tick.  So the parent is the own neighbour of the child's square,
with no action yet this tick, whose RUNNING energy (tick start, plus eats and feeds earlier in the log) is >= 5 and
halves to the child's energy.

    RUN = parents.Running()
    RUN.tick(enOf)                    # at every tick start (enOf = tick-start energies)
    RUN.event(k, a, b)                # for every eat (k == 4) and feed (k == 5) event, in log order
    par, tag = RUN.parent(cands, e)   # at a birth; cands = own neighbours with no action yet
tag: 'match' (one candidate), 'ambiguous' (several; the first is returned: its energy is right, its square may not
be), 'unknown' (candidates, none fits: par is None, keep it out of rate tables), 'none' (no candidate).
RUN.count holds the tags.
"""

import collections


class Running(object):
    def __init__(self):
        self.count = collections.Counter()
        self.start, self.run = {}, {}

    def tick(self, en):
        self.start, self.run = en, {}

    def get(self, c):
        return self.run.get(c, self.start.get(c, 0))

    def event(self, k, a, b):
        if k == 4:
            take = min(2, self.get(b))
            self.run[a], self.run[b] = self.get(a) + take, self.get(b) - take
        elif k == 5:
            give = min(2, self.get(a))
            self.run[a], self.run[b] = self.get(a) - give, self.get(b) + give

    def parent(self, cands, e):
        hit = [g for g in cands if self.get(g) >= 5 and self.get(g) // 2 == e]
        tag = 'match' if len(hit) == 1 else 'ambiguous' if hit else 'unknown' if cands else 'none'
        self.count[tag] += 1
        par = hit[0] if hit else None
        if par is not None:
            self.run[par] = self.get(par) - e
        return par, tag
