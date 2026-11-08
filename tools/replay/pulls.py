"""Shared helpers of the replay tools: where the data pulls are, the --pull argument, colony names.

A data pull is a folder data/<pull>/ (any name).  No tool has a default pull: each one needs --pull <name>.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data')


def _natural(name):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', name)]


def found():
    """The folders of data/ (natural name order, pull2 before pull10), except the splits folder."""
    if not os.path.isdir(DATA):
        return []
    return sorted((p for p in os.listdir(DATA) if os.path.isdir(os.path.join(DATA, p)) and p != 'splits'),
                  key=_natural)


def no_pull(tool):
    """Stop with one line: the tool needs --pull; name the folders found in data/."""
    sys.exit('%s: name the pull with --pull <name> (folders in data/: %s; see "Doing your own pull" in '
             'architecture/data-pulls.md)' % (tool, ', '.join(found()) or 'none'))


def take_pull(argv, tool):
    """(pull, other arguments) from an argument list with --pull NAME or --pull=NAME; stops when it is missing."""
    rest, pull, i = [], None, 0
    while i < len(argv):
        a = argv[i]
        if a == '--pull' and i + 1 < len(argv):
            pull = argv[i + 1]
            i += 2
            continue
        if a.startswith('--pull='):
            pull = a.split('=', 1)[1]
        else:
            rest.append(a)
        i += 1
    if not pull:
        no_pull(tool)
    return pull, rest


def pull_dir(pull, *parts):
    return os.path.join(DATA, pull, *parts)


def clean_name(n):
    """A colony name without a leading emoji (the site shows one); names without one are kept whole."""
    return n.split(' ', 1)[-1] if not n[:1].isalnum() else n


def load_names(pull, rid):
    """Colony names of replay rid in colony order: data/<pull>/names.json (tab.py), else the pull 2 format
    data/<pull>/summaries/<id>.json.  None when neither has the replay."""
    np = pull_dir(pull, 'names.json')
    if os.path.exists(np):
        with open(np, encoding='utf-8') as f:
            names = json.load(f).get(str(rid))
        if names:
            return [clean_name(n) for n in names]
    sp = pull_dir(pull, 'summaries', '%s.json' % rid)
    if os.path.exists(sp):
        with open(sp, encoding='utf-8') as f:
            return [clean_name(n) for n in json.load(f)['names']]
    return None
