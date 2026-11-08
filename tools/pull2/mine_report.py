"""Old path of tools/replay/mine_report.py, kept so that the commands in the dated reports in data/ still run.
For your own pull use:  python -I tools/replay/mine_report.py --pull <pull> ...  (architecture/data-pulls.md).
This file runs it with the defaults this path had: pull2, Sprint against AtomPush and AtomCrasher.  Later arguments replace them."""
import os, runpy, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEW = os.path.join(ROOT, 'tools', 'replay', 'mine_report.py')
sys.argv = [NEW] + ['--pull', 'pull2', '--cell', 'Sprint', '--rivals', 'AtomPush,AtomCrasher'] + sys.argv[1:]
runpy.run_path(NEW, run_name='__main__')
