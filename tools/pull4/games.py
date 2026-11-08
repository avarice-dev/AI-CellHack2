"""Old path of tools/replay/games.py, kept so that the commands in the dated reports in data/ still run.
For your own pull use:  python -I tools/replay/games.py --pull <pull> ...  (architecture/data-pulls.md).
This file runs it with the defaults this path had: pull4, Contagion, rival Scourge.  Later arguments replace them."""
import os, runpy, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEW = os.path.join(ROOT, 'tools', 'replay', 'games.py')
sys.argv = [NEW] + ['--pull', 'pull4', '--cell', 'Contagion', '--rival', 'Scourge'] + sys.argv[1:]
runpy.run_path(NEW, run_name='__main__')
