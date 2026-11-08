"""Old path of tools/replay/tab.py, kept so that the commands in the dated reports in data/ still run.
For your own pull use:  python -I tools/replay/tab.py --pull <pull> ...  (architecture/data-pulls.md).
This file runs it with the defaults this path had: pull3, Scourge, halves, the pull 3 match list.  Later arguments replace them."""
import os, runpy, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEW = os.path.join(ROOT, 'tools', 'replay', 'tab.py')
sys.argv = [NEW] + ['--pull', 'pull3', '--cell', 'Scourge', '--parts', '2', '--matches', os.path.join(ROOT, 'data', 'pull3', 'matches-scourge-2026-11-08.json')] + sys.argv[1:]
runpy.run_path(NEW, run_name='__main__')
