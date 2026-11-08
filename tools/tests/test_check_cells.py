"""unit: the verdict of cells/check_cells.py (no NASM, no Unicorn needed).
Run from the repo root:  python -m unittest discover -s tools/tests
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'cells'))
import check_cells as CC  # noqa: E402


class CheckCellsVerdict(unittest.TestCase):
    """unit: check_cells.verdict() over a problem list; the shelved VEX cells are expected failures."""

    def test_no_problems(self):
        text, code = CC.verdict([])
        self.assertEqual(code, 0)
        self.assertIn('ALL CHECKS PASSED', text)

    def test_only_shelved_vex_cells_fail(self):
        text, code = CC.verdict([('woe', 'a'), ('conceit', 'b'), ('endemic', 'c'), ('endemic', 'd')])
        self.assertEqual(code, 0)
        self.assertIn('4 EXPECTED', text)
        self.assertIn('conceit, endemic, woe', text)

    def test_other_cell_fails(self):
        text, code = CC.verdict([('woe', 'a'), ('scourge', 'b')])
        self.assertEqual(code, 1)
        self.assertIn('1 PROBLEM(S)', text)
        self.assertIn('scourge', text)

    def test_expected_set_is_the_vex_cells(self):
        self.assertEqual(CC.EXPECTED_FAIL, {'woe', 'conceit', 'endemic'})


if __name__ == '__main__':
    unittest.main()
