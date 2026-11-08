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


if __name__ == '__main__':
    unittest.main()


class LoadRealTest(unittest.TestCase):
    def test_missing_races_file_gives_none(self):
        # 98797's raw replay was deleted in pull 2 (size cap), so it has no races file
        self.assertIsNone(T.load_real(98797))
