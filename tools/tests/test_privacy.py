"""Unit tests for tools/privacy_check.py.

Fake local paths and model names are built by concatenation so this file itself passes the check.
Run from the repo root:  python -m unittest discover -s tools/tests
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import privacy_check as pc  # noqa: E402

M = pc.MODEL_WORDS                      # the model words, decoded at run time
DRIVE = 'C' + ':\\Users\\someone\\proj'
WSL = '/mnt' + '/c' + '/Us' + 'ers/someone/proj'
GITBASH = '/c' + '/Us' + 'ers/someone/proj'
HOME = '~' + '/Downloads'


class TestLineChecks(unittest.TestCase):
    def hits(self, line, models=True, personal=()):
        return pc.check_line(line, pc.compile_patterns(models=models, personal=personal))

    def test_local_paths_are_flagged(self):
        for line in (DRIVE, 'see ' + 'D' + ':/data/x.txt', WSL, GITBASH, 'cd ' + HOME,
                     'kept in the scratch' + 'pad', 'a Task ' + 'Scheduler task',
                     'mail me: someone' + '@' + 'mail.org'):
            self.assertTrue(self.hits(line), line)

    def test_clean_lines_pass(self):
        for line in ('start:\n\tret', 'cd sim && python batch.py', 'see data/pull2/x.json',
                     'http' + '://example.org/a', 'mov rax, [rel kEnemy]', 'a: b/c', 'C++ code',
                     'test' + '@' + 'example.com', '$HOME/Downloads', '~~struck~~'):
            self.assertEqual(self.hits(line), [], line)

    def test_model_names_flagged_by_default(self):
        line = 'reviewed by ' + M[1].capitalize() + ' agents'
        self.assertTrue(pc.check_line(line, pc.compile_patterns()))
        self.assertEqual(self.hits(line, models=False), [])           # the --no-models opt-out
        self.assertTrue(self.hits(line))
        self.assertTrue(self.hits('claude-' + M[0] + '-4'))
        self.assertEqual(self.hits('an af' + M[3] + ' person'), [])   # word boundary

    def test_personal_patterns(self):
        pers = ['Users[\\\\/]Someone', 'someone@x\\.org', 'App' + 'Data']
        self.assertTrue(self.hits('x/App' + 'Data/Local', personal=pers))
        self.assertFalse(self.hits('x/App' + 'Data/Local'))     # personal-only, not a generic pattern
        self.assertTrue(self.hits('C' + ':/Us' + 'ers/Someone/x', personal=pers))
        self.assertTrue(self.hits('ask someone' + '@x.org', personal=pers))
        self.assertEqual(self.hits('nothing here', personal=pers), [])

    def test_read_personal_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, '.privacy-patterns')
            with open(p, 'w') as f:
                f.write('# comment\n\nUsers[\\\\/]Someone\n')
            self.assertEqual(pc.read_personal(p), ['Users[\\\\/]Someone'])
            self.assertEqual(pc.read_personal(os.path.join(d, 'missing')), [])


class TestScan(unittest.TestCase):
    def test_scan_dir_reports_file_line_and_skips_binary(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'a.md'), 'w') as f:
                f.write('ok\nsee ' + WSL + '\n')
            with open(os.path.join(d, 'b.bin'), 'wb') as f:
                f.write(b'\x00\x01' + WSL.encode())
            with open(os.path.join(d, 'c.md'), 'w') as f:
                f.write('clean\n')
            hits = pc.scan_paths([d], pc.compile_patterns())
            self.assertEqual([(os.path.basename(h[0]), h[1]) for h in hits], [('a.md', 2)])

    def test_long_lines_are_truncated(self):
        line = 'x' * 500 + ' ' + WSL
        out = pc.format_hit('f.md', 1, line, 'local path')
        self.assertLess(len(out), 260)
        self.assertIn('f.md:1', out)

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good = os.path.join(d, 'good.md')
            bad = os.path.join(d, 'bad.md')
            with open(good, 'w') as f:
                f.write('fine\n')
            with open(bad, 'w') as f:
                f.write(GITBASH + '\n')
            nopers = os.path.join(d, 'none')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(pc.main(['--patterns', nopers, good]), 0)
                self.assertEqual(pc.main(['--patterns', nopers, bad]), 1)

    def test_main_flags_model_names_unless_no_models(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, 'm.md')
            with open(f, 'w') as fh:
                fh.write('written with ' + M[0].capitalize() + '\n')
            nopers = os.path.join(d, 'none')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(pc.main(['--patterns', nopers, f]), 1)
                self.assertEqual(pc.main(['--patterns', nopers, '--no-models', f]), 0)


if __name__ == '__main__':
    unittest.main()
