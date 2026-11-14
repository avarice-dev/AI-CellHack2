"""Hold-off study (2026-11-13): make_misfortune variants vs Misfortune as built, Stage 2 line-up and pairing.
Variant name: 'B1' (as built) or 'B1:hold=split:hold_min=8'.  python hold_off_runner.py --ticks 1000 --variants ... --seeds 1-8"""
import argparse, json, os, sys, time, multiprocessing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misfortune_runner as M
import cells_ref as C
import engine as E

M.CHECK_TICKS = (30, 60, 100, 300, 600, 1000, 2000, 3000)
VARIANTS = {
    'base': {}, 'off': dict(hold='off'), 'split5': dict(hold='split', hold_min=5),
    'split8': dict(hold='split', hold_min=8), 'split10': dict(hold='split', hold_min=10),
    'split12': dict(hold='split', hold_min=12),
}


M2 = {'misfortune2': {}, 'm2v0': {}, 'm2v1': dict(hold='off', hold_min=5),
      'm2v2': dict(hold='off', hold_min=5, threat_min=5),
      'm2v3': dict(hold='off', hold_min=5, threat_min=5, refill_min=8, fire_min=8),
      'ac0': dict(armed_children=True), 'ac1': dict(armed_children=True, hold='off', hold_min=5),
      'ac1_allodd': dict(armed_children='allodd', hold='off', hold_min=5),
      'ac2': dict(armed_children=True, hold='split', hold_min=5)}   # enemy-gated: a diagonal enemy + e >= 5 splits


def policy(name):
    if name in M2:
        return C.make_misfortune2(**M2[name])
    return C.make_misfortune(cap='B', exact=1, **VARIANTS[name])


def play(job):
    seat, name = job['seat'], job['variant']
    meter = M.Meter(seat, policy(name))
    pols = [M.other_policy(n) for n in M.OPPONENTS]
    pols.insert(seat, meter.policy)
    eng = E.Engine(pols, seed=job['seed'], max_ticks=job['ticks'], start_mode='random', record_races=True)
    meter.attach(eng)
    dth = {}
    while True:
        more = eng.step()
        meter.after_tick()
        if eng.tick in M.CHECK_TICKS:
            dth[str(eng.tick)] = [eng.deaths[seat], eng.births[seat]]
        if not more:
            break
    places = {r['colony']: r['place'] for r in eng.ranking()}
    out = {'key': '%s|%d|%d' % (name, job['seed'], job['ticks']), 'variant': name, 'seed': job['seed'], 'seat': seat,
           'ticks': job['ticks'], 'place': places[seat], 'cells': eng.pop[seat], 'deaths_births': dth}
    out.update(meter.result())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ticks', type=int, default=1000)
    ap.add_argument('--variants', default='base,off,split5,split8,split10')
    ap.add_argument('--seeds', default='1,2,3,4,5,6,7,8')
    ap.add_argument('--log', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'hold-off.jsonl'))
    ap.add_argument('--workers', type=int, default=4, help='parallel games (cap 4 of 6 cores, below-normal priority)')
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(',')]
    done = set()
    if os.path.exists(a.log):
        done = {json.loads(l)['key'] for l in open(a.log) if l.strip()}
    jobs = [dict(variant=v, seed=s, seat=M.seat_for(s), ticks=a.ticks) for s in seeds for v in a.variants.split(',')]
    jobs = [j for j in jobs if '%s|%d|%d' % (j['variant'], j['seed'], j['ticks']) not in done]
    print(len(jobs), 'games', flush=True)
    t0 = time.time()
    with multiprocessing.get_context('spawn').Pool(a.workers) as pool:
        for k, r in enumerate(pool.imap_unordered(play, jobs, chunksize=1), 1):
            with open(a.log, 'a') as f:
                f.write(json.dumps(r, sort_keys=True) + '\n')
            print('[%d/%d] %s s%d cells %d (%.0fs)' % (k, len(jobs), r['variant'], r['seed'], r['cells'], time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
