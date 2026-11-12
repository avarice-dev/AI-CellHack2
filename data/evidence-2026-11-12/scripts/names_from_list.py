"""Scratch: data/<pull>/names.json from our match list (colonies in colony order), Bane labelled by match id.
Keeps entries already in names.json.  Usage: python names_from_list.py <ourmatches.json> <names.json>
"""
import json
import os
import sys

lst = json.load(open(sys.argv[1], encoding='utf-8'))
out = json.load(open(sys.argv[2], encoding='utf-8')) if os.path.exists(sys.argv[2]) else {}


def clean(n):
    return n.split(' ', 1)[-1] if not n[:1].isalnum() else n


def label(n, rid):
    if n != 'Bane':
        return n
    return 'Bane v1' if rid < 124690 else 'Bane v2.0' if rid < 126000 else 'Bane v2.1' if rid < 127810 else 'Bane v2.2'


for r in lst['rows']:
    out.setdefault(str(r['id']), [label(clean(c), r['id']) for c in r['colonies']])
with open(sys.argv[2], 'w', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, ensure_ascii=False, indent=0)
print(len(out), 'entries')
