"""Engine extensions: start placement modes, stun/memory flag, action counters, bite-order pairs.

Integration tests of engine.py with scripted policies (nothing of ours faked).
"""

import unittest

from .helpers import E, board, script, eat, feed, move, split, REST, RIGHT, LEFT, UP, DOWN, NOP
import bots


def starts(eng):
    return sorted((c, x, y) for _, x, y, c, _ in eng.cells())


def dist(a, b, metric):
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dx, dy) if metric == 'chebyshev' else dx + dy


class StartPlacementTest(unittest.TestCase):
    def test_corner_mode_is_the_engine_default(self):
        e = E.Engine([bots.idle] * 4, width=10, height=8)
        self.assertEqual(starts(e), [(0, 0, 0), (1, 9, 0), (2, 0, 7), (3, 9, 7)])
        e = E.Engine([bots.idle] * 4, width=10, height=8, start_mode='corner', start_inset=1)
        self.assertEqual(starts(e), [(0, 1, 1), (1, 8, 1), (2, 1, 6), (3, 8, 6)])

    def test_random_mode_respects_min_distance_and_board(self):
        for metric in ('manhattan', 'chebyshev'):
            for seed in range(40):
                e = E.Engine([bots.idle] * 4, seed=seed, start_mode='random', start_min_dist=12,
                             start_metric=metric)
                pts = [(x, y) for _, x, y in starts(e)]
                self.assertEqual(len(pts), 4)
                for x, y in pts:
                    self.assertTrue(0 <= x < 64 and 0 <= y < 64)
                for i in range(4):
                    for j in range(i + 1, 4):
                        self.assertGreaterEqual(dist(pts[i], pts[j], metric), 12, (metric, seed, pts))

    def test_random_default_metric_is_manhattan_8(self):
        # Pull 2 (36 replays): the closest pair of starts is Manhattan 8 at the least (98862, 98879,
        # 99324), so the default must admit those real start sets; 98753 has a Chebyshev-11 pair.
        self.assertEqual(E.DEFAULT_START_MIN_DIST, 8)
        self.assertEqual(E.DEFAULT_START_METRIC, 'manhattan')
        for pts in ([(10, 61), (23, 30), (45, 21), (13, 41)], [(29, 49), (32, 23), (52, 36), (29, 57)],
                    [(22, 47), (8, 33), (13, 36), (15, 23)], [(54, 53), (45, 48), (35, 30), (34, 23)]):
            self.assertTrue(E.starts_ok(pts, E.DEFAULT_START_MIN_DIST, 'manhattan'), pts)
        self.assertFalse(E.starts_ok([(29, 49), (32, 23), (52, 36), (29, 57)], 9, 'manhattan'))

    def test_random_mode_is_seeded_and_varies(self):
        def s(seed):
            return starts(E.Engine([bots.idle] * 4, seed=seed, start_mode='random'))
        self.assertEqual(s(5), s(5))
        self.assertEqual(len({tuple(s(k)) for k in range(10)}), 10)

    def test_random_mode_is_roughly_uniform(self):
        xs, ys = [], []
        for seed in range(300):
            for _, x, y in starts(E.Engine([bots.idle, bots.idle], seed=seed, start_mode='random')):
                xs.append(x)
                ys.append(y)
        self.assertAlmostEqual(sum(xs) / len(xs), 31.5, delta=3)
        self.assertAlmostEqual(sum(ys) / len(ys), 31.5, delta=3)
        self.assertLess(min(xs), 4)
        self.assertGreater(max(xs), 59)

    def test_only_present_slots_get_a_cell(self):
        e = E.Engine([bots.idle, None, bots.idle], seed=1, start_mode='random')
        self.assertEqual([c for c, _, _ in starts(e)], [0, 2])

    def test_impossible_distance_raises(self):
        with self.assertRaises(ValueError):
            E.Engine([bots.idle] * 4, width=8, height=8, start_mode='random', start_min_dist=12)

    def test_fixed_positions(self):
        e = E.Engine([bots.idle] * 4, start_mode='fixed',
                     start_positions=[(10, 61), (23, 30), (45, 21), (13, 41)])
        self.assertEqual(starts(e), [(0, 10, 61), (1, 23, 30), (2, 45, 21), (3, 13, 41)])

    def test_custom_sampler_gets_match_rng(self):
        seen = []

        def sampler(rng, w, h, n):
            seen.append((w, h, n, rng.random()))
            return [(k, k) for k in range(n)]
        e = E.Engine([bots.idle] * 3, width=9, height=7, seed=3, start_mode='random', start_sampler=sampler)
        self.assertEqual(starts(e), [(0, 0, 0), (1, 1, 1), (2, 2, 2)])
        import random
        self.assertEqual(seen, [(9, 7, 3, random.Random(3).random())])

    def test_named_sampler(self):
        self.assertIn('uniform', E.START_SAMPLERS)
        e = E.Engine([bots.idle] * 2, seed=2, start_mode='random', start_sampler='uniform')
        self.assertEqual(len(starts(e)), 2)

    def test_bad_mode_raises(self):
        with self.assertRaises(ValueError):
            E.Engine([bots.idle], start_mode='diagonal')


class StunMemoryFlagTest(unittest.TestCase):
    def play(self, keep, bite_insn):
        def p0(view, mem):
            return eat(RIGHT), bite_insn

        def p1(view, mem):
            mem[5] += 1
            return REST, 5
        e = board([p0, p1], stun_keeps_memory=keep)
        e.add_cell(1, 1, 0, 10)
        b = e.add_cell(2, 1, 1, 20)
        e.step()
        return e.c_mem[b][5]

    def test_default_keeps_writes_of_stunned_cell(self):
        self.assertEqual(self.play(True, 1), 1)

    def test_drop_mode_discards_writes_of_stunned_cell(self):
        self.assertEqual(self.play(False, 1), 0)

    def test_drop_mode_keeps_writes_when_bitten_after_its_turn(self):
        self.assertEqual(self.play(False, 9), 1)

    def test_drop_mode_unbitten_cells_keep_writes(self):
        def p(view, mem):
            mem[0] += 1
            return REST, 2
        e = board([p], stun_keeps_memory=False)
        a = e.add_cell(1, 1, 0, 10)
        e.step()
        e.step()
        self.assertEqual(e.c_mem[a][0], 2)


class CounterTest(unittest.TestCase):
    def test_moves_feeds_eats_counted_when_they_happen(self):
        p0 = script({(0, 0): (move(RIGHT), 1),          # succeeds
                     (0, 4): (move(UP), 1),             # blocked by own cell at (0,3)
                     (0, 3): (feed(RIGHT), 2),          # feeds friend at (1,3)
                     (1, 3): (eat(RIGHT), 3),           # eats enemy at (2,3)
                     (4, 4): (eat(LEFT), 4)},           # eats friend at (3,4)
                    default=NOP)
        e = board([p0, script({}, default=NOP)], record_events=True)
        for x, y in ((0, 0), (0, 4), (0, 3), (1, 3), (4, 4), (3, 4)):
            e.add_cell(x, y, 0, 10)
        e.add_cell(2, 3, 1, 10)
        e.add_cell(4, 0, 1, 10)
        e.step()
        self.assertEqual(e.moves, [1, 0, 0, 0])
        self.assertEqual(e.feeds, [1, 0, 0, 0])
        self.assertEqual(e.eats_enemy, [1, 0, 0, 0])
        self.assertEqual(e.eats_friend, [1, 0, 0, 0])

    def test_failed_eat_and_feed_not_counted(self):
        p0 = script({(1, 1): (eat(RIGHT), 1), (1, 2): (feed(RIGHT), 1)})
        e = board([p0])
        e.add_cell(1, 1, 0, 10)
        e.add_cell(1, 2, 0, 10)
        e.step()
        self.assertEqual((e.eats_enemy[0], e.eats_friend[0], e.feeds[0]), (0, 0, 0))


class SplitEnergyTest(unittest.TestCase):
    """record_events: split_energy[c] = {parent energy before the split: count} (ladder data s4)."""

    def test_parent_energy_histogram(self):
        p0 = script({(1, 1): (split(RIGHT), 1), (1, 3): (split(RIGHT), 1), (3, 3): (split(UP), 1)})
        e = board([p0], record_events=True)
        e.add_cell(1, 1, 0, 6)
        e.add_cell(1, 3, 0, 6)
        e.add_cell(3, 3, 0, 9)
        e.add_cell(4, 4, 0, 4)     # never splits
        e.step()
        self.assertEqual(e.split_energy[0], {6: 2, 9: 1})
        self.assertEqual(e.split_energy[1], {})

    def test_off_by_default(self):
        e = board([script({(1, 1): (split(RIGHT), 1)})])
        e.add_cell(1, 1, 0, 6)
        e.step()
        self.assertIsNone(e.split_energy)


class BiteOrderTest(unittest.TestCase):
    def setup(self, record):
        # colony 0 bites at 1 and 3 instructions, colony 1 at 2, all in the same tick
        p0 = script({(0, 0): (eat(RIGHT), 1), (4, 0): (eat(LEFT), 1), (0, 4): (eat(RIGHT), 3)})
        p1 = script({(4, 2): (eat(LEFT), 2)})
        e = board([p0, p1, script({})], record_events=record)
        e.add_cell(0, 0, 0, 10)
        e.add_cell(1, 0, 2, 10)
        e.add_cell(0, 4, 0, 10)
        e.add_cell(1, 4, 2, 10)
        e.add_cell(4, 0, 0, 10)
        e.add_cell(3, 0, 2, 10)
        e.add_cell(4, 2, 1, 10)
        e.add_cell(3, 2, 2, 10)
        return e

    def test_all_ordered_pairs_of_same_tick_eats(self):
        e = self.setup(True)
        e.step()
        m = e.bite_first
        self.assertEqual(m[0][1], 2)      # c0's two 1-insn eats before c1's
        self.assertEqual(m[1][0], 1)      # c1's eat before c0's 3-insn eat
        self.assertEqual(m[0][0], 0)      # same colony is not a pair
        self.assertEqual(sum(map(sum, m)), 3)
        e.step()                           # targets still alive (8 energy): the same bites again
        self.assertEqual(sum(map(sum, e.bite_first)), 6)

    def test_off_by_default(self):
        e = self.setup(False)
        e.step()
        self.assertIsNone(e.bite_first)


class FeedBonusTest(unittest.TestCase):
    """feed_bonus: the receiver gains FEED_AMOUNT + bonus (ladder pull 2: receivers usually end +3)."""

    def play(self, **kw):
        p0 = script({(1, 1): (feed(RIGHT), 1)})
        e = board([p0], **kw)
        e.add_cell(1, 1, 0, 10)
        b = e.add_cell(2, 1, 0, 20)
        e.step()
        return e.c_en[b], e.c_en[0]

    def test_default_is_plus_2(self):
        self.assertEqual(self.play(), (22, 8))

    def test_bonus_1_gives_plus_3_feeder_still_pays_2(self):
        self.assertEqual(self.play(feed_bonus=1), (23, 8))

    def test_bonus_respects_cap(self):
        p0 = script({(1, 1): (feed(RIGHT), 1)})
        e = board([p0], feed_bonus=1)
        e.add_cell(1, 1, 0, 10)
        b = e.add_cell(2, 1, 0, 49)
        e.step()
        self.assertEqual(e.c_en[b], 50)


class IdleGainTest(unittest.TestCase):
    """idle_gain_prob: a cell with no event this tick and no REST gains +1 with that probability."""

    def test_off_by_default(self):
        e = board([script({})])
        a = e.add_cell(1, 1, 0, 10)
        for _ in range(5):
            e.step()
        self.assertEqual(e.c_en[a], 10)

    def test_prob_1_every_idle_tick(self):
        e = board([script({})], idle_gain_prob=1.0)
        a = e.add_cell(1, 1, 0, 10)
        for _ in range(5):
            e.step()
        self.assertEqual(e.c_en[a], 15)

    def test_rest_moves_and_bitten_cells_do_not_gain(self):
        p0 = script({(0, 0): (REST, 1), (4, 4): (move(LEFT), 1), (2, 2): (eat(RIGHT), 1)})
        e = board([p0, script({})], idle_gain_prob=1.0)
        r = e.add_cell(0, 0, 0, 10)
        m = e.add_cell(4, 4, 0, 10)
        a = e.add_cell(2, 2, 0, 10)
        b = e.add_cell(3, 2, 1, 10)
        e.step()
        self.assertEqual((e.c_en[r], e.c_en[m], e.c_en[a], e.c_en[b]), (11, 10, 12, 8))

    def test_half_and_match_rng_untouched(self):
        def run(p):
            e = E.Engine([script({})] * 4, width=40, height=40, seed=7, max_ticks=1, start_mode='random',
                         idle_gain_prob=p)
            e2 = board([script({})], w=40, h=40, seed=7, idle_gain_prob=p)
            ids = [e2.add_cell(x, y, 0, 10) for x in range(40) for y in range(0, 40, 4)]
            e2.step()
            return e.start_positions, e.rng.random(), sum(e2.c_en[i] - 10 for i in ids), len(ids)
        s0, r0, g0, _ = run(0.0)
        s1, r1, g1, n = run(0.5)
        self.assertEqual((s0, r0, g0), (s1, r1, 0))
        self.assertTrue(0.4 * n < g1 < 0.6 * n, (g1, n))


class DeltaRecordTest(unittest.TestCase):
    """record_deltas: energy change over the tick per cell-tick, split into no-event and fed-once cases,
    to compare with the replay statistics (pull 2 section 6)."""

    def test_histograms(self):
        p0 = script({(0, 0): (REST, 1), (4, 0): (feed(DOWN), 1), (4, 1): (REST, 2), (2, 4): (feed(RIGHT), 1),
                     (3, 4): (eat(RIGHT), 3)})
        e = board([p0, script({})], record_deltas=True)
        e.add_cell(0, 0, 0, 10)       # rests: no event, +1
        e.add_cell(0, 2, 0, 10)       # NOP: no event, 0
        e.add_cell(0, 4, 0, 50)       # NOP at the cap
        e.add_cell(4, 0, 0, 20)       # feeder (event)
        e.add_cell(4, 1, 0, 10)       # fed once and rests: +3
        e.add_cell(2, 4, 0, 20)       # feeder
        e.add_cell(3, 4, 0, 10)       # fed, also eats: two events, not in 'fed'
        e.add_cell(4, 4, 1, 10)       # bitten (event)
        e.step()
        self.assertEqual(e.deltas['idle'], {1: 1, 0: 2})
        self.assertEqual(e.deltas['fed'], {3: 1})

    def test_off_by_default(self):
        self.assertIsNone(board([script({})]).deltas)


if __name__ == '__main__':
    unittest.main()
