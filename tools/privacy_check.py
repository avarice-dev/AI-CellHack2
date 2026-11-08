#!/usr/bin/env python3
"""Flag machine-specific or personal text before it is committed or shared.

    python tools/privacy_check.py                  # all tracked text files (ops/ excluded)
    python tools/privacy_check.py --staged         # staged content (used by tools/hooks/pre-commit)
    python tools/privacy_check.py --models DIR     # a folder (used by tools/export_share.py)
    python tools/privacy_check.py FILE ...         # given files or folders

Two pattern sets:
  * generic local-path / local-plumbing patterns, kept in this file (no personal data here);
  * personal patterns (user name folder, email, ...) read from `.privacy-patterns` at the repo root:
    one Python regex per line, `#` comments allowed.  That file is git-ignored and never shared.
`--models` also flags model names (only the export needs that; working files may name models).
Binary files (a NUL byte in the first 8 KB) are skipped.  Exit status 1 when anything is flagged.
"""
import argparse
import codecs
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_PREFIXES = ('ops/',)                # local plumbing, never shared, not checked
EXCLUDE_FILES = ('.privacy-patterns',)
PATTERNS_FILE = '.privacy-patterns'
MAX_SHOWN = 160

# Model words, rot13-encoded so this file (which is shared) contains none of them in clear text.
MODEL_WORDS = codecs.decode('bchf fbaarg unvxh snoyr', 'rot13').split()
MODEL_ALT = '|'.join(MODEL_WORDS)

GENERIC = [
    # drive-letter paths with at least one full folder component
    ('drive path', r'(?<![A-Za-z0-9_%\\])[A-Za-z]:(?:/|\\{1,2})[A-Za-z0-9_.$ ~-]{2,}?[\\/]'),
    ('drive path', r'(?<![A-Za-z0-9_%\\])[A-Za-z]:[\\/]+(?:Users|Program Files|ProgramData|Windows)\b'),
    ('WSL path', r'/mnt/[A-Za-z]/'),
    ('Git Bash path', r'(?<![\w.~-])/[A-Za-z]/(?:Users|home|Program Files|ProgramData|Windows)\b'),
    ('home path', r'(?<![\w.])/(?:home|Users)/[\w.-]+'),
    ('home path', r'(?<![\w~])~(?:/|\\)'),
    ('user config dir', r'\.claude[\\/]'),
    ('session scratch dir', r'(?i)scratch[p]ad'),
    ('local scheduler', r'(?i)Task\s+Schedul[e]r|schtask[s]'),
    ('email', r'[\w.+-]+@(?!example\.(?:com|org|net)\b)[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}\b(?<!noreply@anthropic\.com)'),
]
MODELS = [
    ('model name', r'(?i)(?<![A-Za-z])(?:' + MODEL_ALT + r')(?![A-Za-z])'),
    ('model id', r'(?i)claude-(?:' + MODEL_ALT + r')-'),
]


def repo_root():
    try:
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=HERE, capture_output=True,
                             text=True, check=True).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.CalledProcessError):
        pass
    return os.path.dirname(HERE)


def read_personal(path):
    """Regex lines from the untracked personal patterns file; [] when it does not exist."""
    try:
        with open(path, encoding='utf-8') as f:
            lines = [ln.strip() for ln in f]
    except FileNotFoundError:
        return []
    return [ln for ln in lines if ln and not ln.startswith('#')]


def compile_patterns(models=False, personal=()):
    pats = [(label, re.compile(rx)) for label, rx in GENERIC]
    pats += [('personal pattern', re.compile(rx, re.IGNORECASE)) for rx in personal]
    if models:
        pats += [(label, re.compile(rx)) for label, rx in MODELS]
    return pats


def check_line(line, pats):
    """[(label, match start)] for every pattern that matches the line."""
    out = []
    for label, rx in pats:
        m = rx.search(line)
        if m:
            out.append((label, m.start()))
    return out


def format_hit(path, lineno, line, label, start=0):
    line = line.rstrip('\r\n')
    if len(line) > MAX_SHOWN:
        a = max(0, min(start - MAX_SHOWN // 3, len(line) - MAX_SHOWN))
        line = ('...' if a else '') + line[a:a + MAX_SHOWN] + ('...' if a + MAX_SHOWN < len(line) else '')
    return '%s:%d: [%s] %s' % (path, lineno, label, line)


def is_binary(data):
    return b'\0' in data[:8192]


def scan_bytes(name, data, pats):
    if is_binary(data):
        return []
    hits = []
    for n, line in enumerate(data.decode('utf-8', errors='replace').splitlines(), 1):
        found = check_line(line, pats)
        if found:
            hits.append((name, n, line, ', '.join(sorted({lb for lb, _ in found})), found[0][1]))
    return hits


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d != '.git')
                for fn in sorted(filenames):
                    yield os.path.join(dirpath, fn)
        else:
            yield p


def scan_paths(paths, pats):
    hits = []
    for fp in iter_files(paths):
        if os.path.basename(fp) in EXCLUDE_FILES:
            continue
        with open(fp, 'rb') as f:
            hits += scan_bytes(fp, f.read(), pats)
    return hits


def excluded(rel):
    rel = rel.replace('\\', '/')
    return rel.startswith(EXCLUDE_PREFIXES) or rel in EXCLUDE_FILES


def git_lines(root, *args):
    out = subprocess.run(['git'] + list(args), cwd=root, capture_output=True, check=True).stdout
    return [x.decode('utf-8') for x in out.split(b'\0') if x]


def scan_staged(root, pats):
    hits = []
    for rel in git_lines(root, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'):
        if excluded(rel):
            continue
        data = subprocess.run(['git', 'show', ':' + rel], cwd=root, capture_output=True, check=True).stdout
        hits += scan_bytes(rel, data, pats)
    return hits


def scan_tracked(root, pats):
    hits = []
    for rel in git_lines(root, 'ls-files', '-z'):
        fp = os.path.join(root, rel)
        if excluded(rel) or not os.path.isfile(fp):
            continue
        with open(fp, 'rb') as f:
            hits += scan_bytes(rel, f.read(), pats)
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('paths', nargs='*', help='files or folders (default: all tracked files)')
    ap.add_argument('--staged', action='store_true', help='check the staged content of staged files')
    ap.add_argument('--models', action='store_true', help='also flag model names')
    ap.add_argument('--patterns', help='personal patterns file (default: <repo root>/%s)' % PATTERNS_FILE)
    a = ap.parse_args(argv)
    root = repo_root()
    personal = read_personal(a.patterns or os.path.join(root, PATTERNS_FILE))
    pats = compile_patterns(models=a.models, personal=personal)
    if a.staged:
        hits = scan_staged(root, pats)
    elif a.paths:
        hits = scan_paths(a.paths, pats)
    else:
        hits = scan_tracked(root, pats)
    for h in hits:
        print(format_hit(*h))
    if hits:
        print('privacy_check: %d flagged line(s). Use repo-relative paths and generic wording.' % len(hits),
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
