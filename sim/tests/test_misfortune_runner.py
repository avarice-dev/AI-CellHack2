"""Tests of sim/misfortune_runner.py: every counter on a small hand-made board, determinism, and the engine hooks.

Integration tests: the real engine (sim/engine.py) with scripted policies (tests/helpers.script) or our reference
cells; nothing of ours is mocked.  Each scenario fixes what the subject and its neighbours do tick by tick, and the
expected counts follow from the rules (turn order by instruction count, a bitten cell is stunned, Tidy removes the
dead) and from the counter definitions in the runner's docstring and briefs/misfortune-spec-2026-11-13.md.
EngineHookTest: the hooks are measurement only: a fixed-seed game of our old cells gives the digest recorded with the
engine before the hooks were added (computed 2026-11-13 from the committed engine), with and without a Meter.
"""

import hashlib
import unittest

import cells_ref
import engine as E
import misfortune_runner as M
from .helpers import board, script

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
EAT, FEED, SPLIT, REST, NOP = 0x30, 0x40, 0x20, 0x01, 0x00
PULL = cells_ref.MISFORTUNE_PULL_N


def subject(table, default=(NOP, 1)):
    """A scripted subject that the Meter treats as Misfortune cap B, exact 1 (armed bite = count 2)."""
    pol = script(table, default)
    pol.cap, pol.exact = 'B', 1
    return pol


def setup(sub, others, w=7, h=5, cells=()):
    """Colony 0 = the subject behind a Meter; others = policies of colonies 1..; cells = (x, y, colony, energy)."""
    meter = M.Meter(0, sub)
    eng = board([meter.policy] + list(others), w=w, h=h, record_races=True)
    meter.attach(eng)
    ids = [eng.add_cell(x, y, c, e) for x, y, c, e in cells]
    return eng, meter, ids


def run(eng, meter, ticks):
    for _ in range(ticks):
        eng.step()
        meter.after_tick()
    return meter.result()


class CounterTest(unittest.TestCase):
    def test_contested_pair_ticks(self):
        """Subject bites RIGHT at 2, the enemy bites LEFT at 3, three ticks: tick 0 has no previous adjacency, so 2
        contested pair-ticks, ours first in both.  With the enemy at 1, ours is second."""
        for en_n, first in ((3, 1), (1, 0)):
            eng, m, _ = setup(subject({}, (EAT + RIGHT, 2)), [script({}, (EAT + LEFT, en_n)), script({})],
                              cells=((1, 2, 0, 30), (2, 2, 1, 30), (6, 0, 2, 10)))
            r = run(eng, m, 3)
            self.assertEqual(r['contested'], {'1|<100|%d' % first: 2})
            self.assertEqual(r['contested_hi'], {})

    def test_contested_high_energy(self):
        eng, m, _ = setup(subject({}, (EAT + RIGHT, 2)), [script({}, (EAT + LEFT, 3)), script({})],
                          cells=((1, 2, 0, 45), (2, 2, 1, 30), (6, 0, 2, 10)))
        r = run(eng, m, 2)                             # tick 1 (the contested one): our energy 47
        self.assertEqual(r['contested_hi'], {'1|1': 1})

    def test_not_contested_when_enemy_bites_elsewhere(self):
        eng, m, _ = setup(subject({}, (EAT + RIGHT, 2)), [script({}, (EAT + UP, 3)), script({})],
                          cells=((1, 2, 0, 30), (2, 2, 1, 30), (6, 0, 2, 10)))
        self.assertEqual(run(eng, m, 3)['contested'], {})

    def test_paths_and_contact_energy(self):
        """Tick 0: armed bite in contact (count 2) at 49; tick 1: energy 50 (capped), a rest (count 7) in contact."""
        eng, m, _ = setup(subject({(0, 1, 2): (EAT + RIGHT, 2), (1, 1, 2): (REST, 7)}), [script({}), script({})],
                          cells=((1, 2, 0, 49), (2, 2, 1, 30), (6, 0, 2, 10)))
        r = run(eng, m, 2)
        self.assertEqual(r['paths'], {'armed/2/1': 1, 'rest/7/1': 1})
        self.assertEqual(r['contact_ticks'], 2)
        self.assertEqual(r['contact_energy'], {'<100|all': 2, '<100|47+': 2, '<100|49': 1, '<100|50': 1})

    def _stuck_then(self, other_table, tick_end=3, extra=()):
        """Subject at (1, 2) bites RIGHT at 2 into an empty square on ticks 0..tick_end-1, then rests (count 9)."""
        tbl = {(t, 1, 2): (EAT + RIGHT, 2) for t in range(tick_end)}
        eng, m, ids = setup(subject(tbl, (REST, 9)), [script(other_table), script({})],
                            cells=((1, 2, 0, 20), (6, 0, 2, 10)) + tuple(extra))
        return eng, m, ids

    def test_stuck_episode_ended_by_feed(self):
        """A friend below (colony 0 is scripted by the subject table: (1, 3) feeds UP at count 5 on tick 2)."""
        tbl = {(t, 1, 2): (EAT + RIGHT, 2) for t in range(3)}
        tbl[(2, 1, 3)] = (FEED + UP, 5)
        eng, m, _ = setup(subject(tbl, (NOP, 1)), [script({}), script({})],
                          cells=((1, 2, 0, 20), (1, 3, 0, 20), (6, 0, 2, 10)))
        r = run(eng, m, 5)
        self.assertEqual((r['armed_eats'], r['armed_fail']), (3, 3))
        self.assertEqual(r['episodes'], [[3, 'feed']])

    def test_stuck_episode_ended_by_bite(self):
        """An enemy at (1, 1) bites DOWN on tick 1 at count 1: the subject is stunned (no armed eat that tick)."""
        eng, m, _ = self._stuck_then({(1, 1, 1): (EAT + DOWN, 1)}, extra=((1, 1, 1, 20),))
        r = run(eng, m, 4)
        self.assertEqual(r['episodes'], [[1, 'bitten'], [1, 'other']])
        self.assertEqual(r['armed_fail'], 2)

    def test_stuck_episode_ended_by_enemy_refill(self):
        """Tick 0 the bite fails; on tick 1 an enemy at (3, 2) moves LEFT into (2, 2) at count 1, before the
        subject's count-2 bite, which lands on ticks 1 and 2."""
        eng, m, _ = self._stuck_then({(1, 3, 2): (0x10 + LEFT, 1)}, extra=((3, 2, 1, 20),))
        r = run(eng, m, 4)
        self.assertEqual(r['episodes'], [[1, 'enemy_refill']])
        self.assertEqual((r['armed_fail'], r['armed_enemy']), (1, 2))

    def test_stuck_episode_ended_by_friend_refill_and_unintended_friendly(self):
        """A friend at (2, 3) moves UP into (2, 2) on tick 1 (count 1, before the subject); the bite then hits it."""
        tbl = {(t, 1, 2): (EAT + RIGHT, 2) for t in range(3)}
        tbl[(1, 2, 3)] = (0x10 + UP, 1)
        eng, m, _ = setup(subject(tbl, (NOP, 1)), [script({}), script({})],
                          cells=((1, 2, 0, 20), (2, 3, 0, 20), (6, 0, 2, 10)))
        r = run(eng, m, 4)
        self.assertEqual(r['episodes'], [[1, 'friend_refill']])
        self.assertEqual((r['armed_fail'], r['armed_friend']), (1, 2))
        self.assertEqual(r['eats_friend'], 2)

    def test_pull_counts_and_cap_loss(self):
        """A boxed-path pull (count PULL_N) by a cell at 49 on a friend at 30: one pull, 1 energy lost to the cap;
        it is not an unintended friendly bite.  A count-PULL_N feed is a lift."""
        tbl = {(0, 1, 2): (EAT + RIGHT, PULL), (1, 1, 2): (FEED + RIGHT, PULL)}
        eng, m, _ = setup(subject(tbl, (NOP, 1)), [script({}), script({})],
                          cells=((1, 2, 0, 49), (2, 2, 0, 30), (6, 0, 2, 10)))
        r = run(eng, m, 2)
        self.assertEqual((r['pulls'], r['pull_cap_loss'], r['lifts'], r['armed_friend']), (1, 1, 1, 0))

    def test_freed_squares(self):
        """The subject kills a 2-energy enemy on tick 0 and splits into its square on tick 1 (us next tick); a
        second kill whose square nobody fills counts empty at 5."""
        tbl = {(0, 1, 2): (EAT + RIGHT, 2), (1, 1, 2): (SPLIT + RIGHT, 3),
               (0, 4, 4): (EAT + RIGHT, 2)}
        eng, m, _ = setup(subject(tbl, (NOP, 1)), [script({}), script({})], w=7, h=6,
                          cells=((1, 2, 0, 20), (2, 2, 1, 2), (4, 4, 0, 20), (5, 4, 1, 2), (6, 0, 2, 10)))
        r = run(eng, m, 8)
        self.assertEqual(r['freed'], {'kills': 2, 'us_t1': 1, 'us_t5': 1, 'empty_t5': 1})

    def test_checks_record_cells_and_energy(self):
        """Rest from 10 (capped at 50), split on tick 100: the t100 check (after ticks 0-99) holds 1 cell, 50."""
        eng, m, _ = setup(subject({(100, 1, 2): (SPLIT + RIGHT, 5)}, (REST, 5)), [script({}), script({})],
                          cells=((1, 2, 0, 10), (6, 0, 1, 10)))
        r = run(eng, m, 102)
        pop, energy = r['checks']['100']
        self.assertEqual((pop[0], energy[0]), (1, 50))
        self.assertEqual(eng.pop[0], 2)


class PlayTest(unittest.TestCase):
    def test_same_seed_and_flags_give_identical_output(self):
        job = {'variant': 'B1', 'seed': 3, 'seat': 2, 'capmid': 0, 'ticks': 40}
        a, b = M.play(job), M.play(job)
        for r in (a, b):
            r.pop('secs')
            r.pop('secs_at')
        self.assertEqual(a, b)
        self.assertEqual(a['names'][2], 'misfortune-B1')

    def test_stage_jobs(self):
        s1 = M.stage_jobs('1', None)
        self.assertEqual(len(s1), 12)
        self.assertEqual({(j['seed'], j['seat']) for j in s1}, {(1, 0), (2, 1), (3, 2), (4, 3)})
        s2 = M.stage_jobs('2', 'B')
        self.assertEqual(len(s2), 16)
        self.assertEqual(sorted(j['seat'] for j in s2 if j['variant'] == 'B1'), [0, 0, 1, 1, 2, 2, 3, 3])
        self.assertTrue(all(j['ticks'] == 3000 for j in s2))
        s3 = M.stage_jobs('3', 'B')
        self.assertEqual(sorted((j['variant'], j['capmid']) for j in s3),
                         [('B0', 0), ('B0', 0), ('B1', 1), ('B1', 1), ('ctrl', 1), ('ctrl', 1)])
        self.assertEqual(len(M.stage_jobs('2', 'B', extra=True)), 32)


def digest(with_meter=False):
    pols = [cells_ref.make_bane2(), cells_ref.make_conviction(), cells_ref.make_penalty(), cells_ref.make_bane3()]
    meter = None
    if with_meter:
        meter = M.Meter(3, pols[3], ctrl=True)
        pols[3] = meter.policy
    eng = E.Engine(pols, seed=5, max_ticks=300, start_mode='random', record_races=with_meter)
    if meter:
        meter.attach(eng)
    h = hashlib.sha256()
    while True:
        more = eng.step()
        if meter:
            meter.after_tick()
        h.update(repr((eng.tick, eng.pop, eng.energy)).encode())
        if not more:
            break
    h.update(repr((eng.ranking(), [bytes(m) for m in eng.c_mem if m is not None][:50])).encode())
    return h.hexdigest()


OLD_ENGINE_DIGEST = '52bf7b1d63a1db7b780047a2b071c7065a05a6c4ef6123e1acbe1e722db888d4'


class EngineHookTest(unittest.TestCase):
    def test_old_cells_game_unchanged(self):
        self.assertEqual(digest(), OLD_ENGINE_DIGEST)

    def test_meter_does_not_change_the_game(self):
        self.assertEqual(digest(with_meter=True), OLD_ENGINE_DIGEST)


if __name__ == '__main__':
    unittest.main()
