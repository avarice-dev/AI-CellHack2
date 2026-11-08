"""treadmill.metrics: unit tests on hand-made race rows (one module, no I/O)."""

import unittest

from . import helpers  # noqa: F401  (puts sim/ on the path)
import treadmill as T

class MetricsTest(unittest.TestCase):
    def test_counts_per_window(self):
        rows = [(10, 0, 1, 0b11, 0, 1, 1, 5),      # colony 0 dies, refills itself, contested 0-1
                (20, 0, 1, 0b11, 1, 1, 1, 4),      # contested, colony 1 wins
                (600, 1, 0, 0b10, 1, 1, 1, 3),     # colony 1 own refill, not contested (0 not adjacent)
                (1500, 1, 0, 0b11, -1, 5, 0, -1)]  # unfilled
        pops = [[1, 1, 0, 0]] * 13 + [[200, 100, 0, 0]] * 50 + [[600, 50, 0, 0]] * 100
        m = T.metrics(rows, pops)
        self.assertEqual(m[0]['deaths'], [2, 0, 0])
        self.assertEqual(m[0]['own'], [1, 0, 0])
        self.assertEqual(m[1]['deaths'], [0, 1, 1])
        self.assertEqual(m[1]['filled'], [0, 1, 0])
        self.assertEqual(m[0]['cont']['1'], [[2, 1], [0, 0], [1, 0]])
        self.assertEqual(m[1]['cont']['0'], [[2, 1], [0, 0], [1, 0]])
        self.assertEqual(m[0]['t128'], 130)
        self.assertEqual(m[0]['t512'], 630)
        self.assertEqual((m[1]['p500'], m[1]['pend']), (100, 50))
        self.assertEqual(m[0]['span'], [500, 500, 620])

    def test_land_check_sim_median_inside_real_range(self):
        def m(p500, pend):
            return {'p500': p500, 'pend': pend}
        real = [('A', None, m(100, 0)), ('A', None, m(100, 50)), ('B', None, m(100, 100)), ('B', None, m(0, 0))]
        sim = [('A', None, m(100, 40)), ('A', None, m(100, 20)), ('B', None, m(100, 150))]
        rows = T.land_check(real, sim, ('A', 'B', 'C'))
        self.assertEqual(rows[0], ('A', -1.0, -0.5, -0.7, True))     # median of -0.6 / -0.8 inside [-1, -0.5]
        self.assertEqual(rows[1], ('B', 0.0, 0.0, 0.5, False))
        self.assertEqual(len(rows), 2)                                # C: no colonies, left out


if __name__ == '__main__':
    unittest.main()
