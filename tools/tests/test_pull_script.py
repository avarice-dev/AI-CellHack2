"""The base pull tools: tools/replay/pull_replays.js (runs in a logged-in browser page) and tools/replay/collect.sh.

Unit (static): the browser script cannot run here (no browser, no site), so these tests read its text: the entry
point, the pacing constants against the site's pacing rules, and the match-list fields that tab.py reads.
e2e (collect.sh): the real script, run by bash in a temporary tree with made-up browser downloads.
Run from the repo root:  python -m unittest discover -s tools/tests
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JS = os.path.join(REPO, 'tools', 'replay', 'pull_replays.js')


class PullScriptText(unittest.TestCase):
    def setUp(self):
        with open(JS, encoding='utf-8') as f:
            self.src = f.read()

    def const(self, name):
        m = re.search(r'const\s+%s\s*=\s*(\d+)\s*;' % name, self.src)
        self.assertIsNotNone(m, name)
        return int(m.group(1))

    def test_entry_point_and_options(self):
        self.assertIn('async function pullReplays(ids, opt)', self.src)
        for word in ('replays', 'CompressionStream', '/api/matches/', '.chr2.gz', 'matches-'):
            self.assertIn(word, self.src)

    def test_pacing_follows_the_site_rules(self):
        self.assertGreaterEqual(self.const('PAGE_GAP_MS'), 15000)       # pages at least 15 s apart
        self.assertGreaterEqual(self.const('REPLAY_GAP_MS'), 30000)     # replays at least 30 s apart
        self.assertGreaterEqual(self.const('BACKOFF_MS'), 60000)        # on 429 or an error wait at least 60 s
        self.assertGreaterEqual(self.const('BACKOFF_MAX_MS'), 300000)   # doubling up to 5 minutes
        self.assertNotIn('Promise.all', self.src)                       # one request at a time

    def test_match_list_schema(self):
        for key in ('utc', 'source', 'note', 'matches', 'id', 'cells', 'winner', 'colonies',
                    'name', 'player', 'place', 'pop', 'peak', 'energy', 'faults', 'insns', 'rating'):
            self.assertRegex(self.src, r'\b%s\b' % key)
        self.assertIn('slice(-9)', self.src)                            # the page table has an empty first cell

    def test_no_personal_or_site_login_data(self):
        for word in ('password', 'csrf', 'cookie'):
            self.assertNotIn(word, self.src.lower())


class CollectMovesTheMatchList(unittest.TestCase):
    def test_match_list_and_replays_land_in_the_pull(self):
        bash = shutil.which('bash')
        if not bash:
            self.skipTest('bash not found')
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, 'tools', 'replay'))
            shutil.copy(os.path.join(REPO, 'tools', 'replay', 'collect.sh'), os.path.join(tmp, 'tools', 'replay'))
            dl = os.path.join(tmp, 'dl')
            os.makedirs(dl)
            for name in ('200.chr2.gz', '201.chr2.gz', 'matches-2026-01-01T00-00-00.json'):
                with open(os.path.join(dl, name), 'wb') as f:
                    f.write(b'x')
            r = subprocess.run([bash, 'tools/replay/collect.sh', 'mypull', 'dl'], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            pull = os.path.join(tmp, 'data', 'mypull')
            self.assertEqual(sorted(os.listdir(os.path.join(pull, 'replays'))), ['200.chr2.gz', '201.chr2.gz'])
            self.assertTrue(os.path.exists(os.path.join(pull, 'matches-2026-01-01T00-00-00.json')))
            self.assertEqual(os.listdir(dl), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
