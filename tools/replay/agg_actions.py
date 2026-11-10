import json, re, sys, collections
root = sys.argv[1]
# optional: python agg_actions.py <root> <pull> <table file>  (one table file, e.g. an energy band)
ONE = sys.argv[2:4]
tot = collections.defaultdict(collections.Counter); cnt = collections.Counter()
for p, fn in ([tuple(ONE)] if ONE else [(q, f'{root}/sim/out/overnight/07-actions-t75-200-{q}.txt') for q in ('pull3', 'pull4', 'pull5')]):
    names = json.load(open(f'{root}/data/{p}/names.json', encoding='utf-8'))
    rid = None
    for line in open(fn, encoding='utf-8'):
        m = re.match(r'##### replay (\d+)', line)
        if m: rid = m.group(1); continue
        m = re.match(r'col (\d) enemy (\S+)\s+n\s+(\d+)\s+(.*)', line)
        if not m or rid not in names: continue
        col, n, rest = int(m.group(1)), int(m.group(3)), m.group(4)
        nm = names[rid][col]
        cnt[nm] += n
        for k, v in re.findall(r'(\S+?) +(\d+)%', rest):
            kk = 'eat' if re.fullmatch(r'e[URDL]', k) else 'feed' if re.fullmatch(r'f[URDL]', k) else k
            tot[nm][kk] += n * int(v) / 100
rows = sorted(cnt, key=lambda k: -cnt[k])
keys = ['eat', 'bitten-first', 'none', 'split?', 'feed']
print('%-12s %8s ' % ('cell', 'n') + ' '.join('%12s' % k for k in keys))
for nm in rows:
    if cnt[nm] < 3000: continue
    print('%-12s %8d ' % (nm, cnt[nm]) + ' '.join('%11.0f%%' % (100 * tot[nm][k] / cnt[nm]) for k in keys))
