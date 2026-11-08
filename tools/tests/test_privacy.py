"""Unit tests for tools/privacy_check.py and the model-name scrub in tools/export_share.py.

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
import export_share as ex  # noqa: E402

M = pc.MODEL_WORDS                      # the model words, decoded at run time
DRIVE = 'C' + ':\\Users\\someone\\proj'
WSL = '/mnt' + '/c' + '/Us' + 'ers/someone/proj'
GITBASH = '/c' + '/Us' + 'ers/someone/proj'
HOME = '~' + '/Downloads'


class TestLineChecks(unittest.TestCase):
    def hits(self, line, models=False, personal=()):
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

    def test_model_names_only_with_models_flag(self):
        line = 'reviewed by ' + M[1].capitalize() + ' agents'
        self.assertEqual(self.hits(line), [])
        self.assertTrue(self.hits(line, models=True))
        self.assertTrue(self.hits('claude-' + M[0] + '-4', models=True))
        self.assertEqual(self.hits('an af' + M[3] + ' person', models=True), [])   # word boundary

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


class TestScrub(unittest.TestCase):
    def test_text_replacements(self):
        big = M[0].capitalize()
        self.assertEqual(ex.scrub_text('the lead (' + big + ')'), 'the lead (Claude)')
        self.assertEqual(ex.scrub_text('Claude ' + M[1].capitalize() + ' 5.5 agents'), 'Claude agents')
        self.assertEqual(ex.scrub_text(M[3].capitalize() + "'s review"), "Claude's review")
        self.assertEqual(ex.scrub_text('--model ' + M[1]), '--model claude')
        self.assertEqual(ex.scrub_text('id claude-' + M[2] + '-4-5 ok'), 'id Claude ok')
        self.assertEqual(ex.scrub_text('af' + M[3] + ' stays'), 'af' + M[3] + ' stays')

    def test_rename_and_link_fix(self):
        old = 'reviews/r3-' + M[3] + '.md'
        renames = ex.plan_renames(['a.md', old, 'reviews/x.md'])
        self.assertEqual(renames, {old: 'reviews/r3-review.md'})
        txt = ex.scrub_text('see `' + old + '` and `r3-' + M[3] + '.md`', renames)
        self.assertEqual(txt, 'see `reviews/r3-review.md` and `r3-review.md`')
        self.assertFalse(pc.check_line(txt, pc.compile_patterns(models=True)))

    def test_rename_collision_is_an_error(self):
        with self.assertRaises(SystemExit):
            ex.plan_renames(['r3-' + M[3] + '.md', 'r3-review.md'])


if __name__ == '__main__':
    unittest.main()
