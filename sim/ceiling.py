"""Self-agreement ceiling: the sim against itself with another seed (same real starts, same models).

python ceiling.py run   -> out/ceiling.json  (the TEST matches x seeds k=1,2,3)
python ceiling.py report [SEED0.json]   (seed 0: a stored validate run of the TEST set, default out/s63-pad3-test.json,
                                         a local output file, not in the repository)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experiments as X
import run as R
import validate as V
import treadmill as T

PAD3 = {"Noob++": "rpump[order=DLRU,hold=none,target=richest,pump_min=5,pump_target_max=50,pad=66,pad_bites_from=1]",
        "rooby": "ratompush[order=URDL,split_min=6,assist_min=99,donor_min=99,pad=56,pad_bites_from=2]",
        "Aegis": "rpump[hold=none,target=richest,pump_min=5,pump_target_max=50,pad=12,pad_bites_from=1]"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'ceiling.json')


def main():
    V.MODELS.update({k: (v, 'model') for k, v in PAD3.items()})
    table = V.load_table()
    fit, test = V.split_sets(table)
    if sys.argv[1] == 'run':
        X.lower_priority()
        ap = __import__('argparse').ArgumentParser(); R.add_engine_args(ap)
        kw = R.engine_kwargs(ap.parse_args([]))
        kw['record_races'] = True
        jobs = [j for j in V.make_jobs({m: table[m] for m in test}, V.load_starts(), kw, 4) if j['game'] >= 1]
        res = X.run_jobs(jobs, 4, lambda r: print('match %d seed %d %.0fs' % (r['mix'], r['seed'], r['secs']), flush=True))
        json.dump(X._jsonable(res), open(OUT, 'w'))
        return
    seed0 = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(OUT), 's63-pad3-test.json')
    if not os.path.exists(seed0) or not os.path.exists(OUT):
        sys.exit('ceiling report needs %s and %s: run "python ceiling.py run" and a stored TEST run first'
                 % (OUT, seed0))
    res = json.load(open(OUT))
    ik = lambda d: {int(k) if str(k).isdigit() else k: v for k, v in d.items()}
    for r in res:
        r['stats'] = [dict(st, pop_at=ik(st['pop_at']), energy_at=ik(st['energy_at']), front_at=ik(st['front_at']),
                           interior_at=ik(st['interior_at'])) for st in (r['stats'].values() if isinstance(r['stats'], dict) else r['stats'])]
        r['deltas'] = {k: ik(v) for k, v in r.get('deltas', {}).items()}
    by = {k: {r['mix']: r for r in res if r['game'] == k} for k in (1, 2, 3)}
    base = {}
    for m, v in json.load(open(seed0)).items():
        base[int(m)] = [v['sim'][str(c)]['pend'] for c in range(4)]
    win = lambda p: max(range(4), key=lambda c: p[c])
    pend = lambda r: [r['treadmill'][str(c)]['pend'] for c in range(4)]
    tot = 0
    for k in (1, 2, 3):
        a = sum(win(base[m]) == win(pend(by[k][m])) for m in test)
        tot += a
        print('winner self-agreement TEST seed 0 vs seed %d: %d/%d' % (k, a, len(test)))
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    W = {0: {m: win(base[m]) for m in test}}
    for k in (1, 2, 3):
        W[k] = {m: win(pend(by[k][m])) for m in test}
    agree = sum(W[a][m] == W[b][m] for a, b in pairs for m in test)
    print('winner self-agreement TEST, all 6 seed pairs: %d/%d = %.1f%%' % (agree, 6 * len(test), 100.0 * agree / (6 * len(test))))
    # checks ceiling: seed k plays "real", seed j is judged against it (k != j among 1..3)
    for k, j in ((1, 2), (2, 3), (3, 1)):
        pseudo = {m: {'freeze': by[k][m]['freeze_tick'],
                      'rows': [dict(cell=n, **V.sim_row(by[k][m], c)) for c, n in enumerate(by[k][m]['cells'])]}
                  for m in test}
        rows = V.thresholds(V.compare(pseudo, [by[j][m] for m in test]))
        ri = [(n, by[k][m]['cells'], by[k][m]['treadmill'][str(c)]) for m in test for c, n in enumerate(by[k][m]['cells'])]
        si = [(n, by[j][m]['cells'], by[j][m]['treadmill'][str(c)]) for m in test for c, n in enumerate(by[j][m]['cells'])]
        lc = T.land_check(ri, si)
        print('seed %d judged on seed %d: checks %d/%d, land %d/%d; failed: %s' % (
            j, k, sum(x[3] for x in rows), len(rows), sum(x[4] for x in lc), len(lc),
            '; '.join(x[0] for x in rows if not x[3]) + ' | land: ' + ', '.join(x[0] for x in lc if not x[4])))




if __name__ == '__main__':
    main()
