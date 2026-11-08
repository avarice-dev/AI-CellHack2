"""Old path of tools/replay/valtab.py, kept so that the commands in the dated reports in data/ still run.
For your own pull use:  python -I tools/replay/valtab.py --pull <pull> ...  (architecture/data-pulls.md).
This file runs it with the defaults this path had: the pull from CH_PULL, default pull3.  Later arguments replace them."""
import os, runpy, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = os.path.join(ROOT, 'tools', 'replay', 'valtab.py')
sys.argv = [NEW] + ['--pull', os.environ.get('CH_PULL', 'pull3')] + sys.argv[1:]
runpy.run_path(NEW, run_name='__main__')
