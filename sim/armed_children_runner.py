"""Armed-children gate v2 (2026-11-13): paired seed+seat, line-up Bane v2.2 / Conviction / Penalty, 3000 ticks.
Variants: split10 (control), m2v0, ac0, ac1, ac2 (see hold_off_runner.M2).  One JSON line per game into the shared folder,
a summary per variant when its seeds are done.  python armed_children_runner.py --stamp 2026-11-13_2340 --workers 6"""
import argparse, json, os, sys, time, statistics, multiprocessing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hold_off_runner as H
import misfortune_runner as M

SHARED = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'shared', 'cellhack2')
VARIANTS = ['split10', 'm2v0', 'ac0', 'ac1', 'ac2']
NAME = 'armed-children-v2'


def flat(r):
    seat, ck, f = r['seat'], r['checks'], r['freed']
    pop = lambda t: ck[str(t)][0][seat]
    db = r['deaths_births']
    ka, ku = r.get('kids_near_a', 0), r.get('kids_near_u', 0)
    t1 = f.get('us_t1', 0) + f.get('enemy_t1', 0)
    return {'variant': r['variant'], 'seed': r['seed'], 'seat': seat, 'cells_t30': pop(30), 'cells_t60': pop(60),
            'cells_t100': pop(100), 'cells_t300': pop(300), 'cells_final': r['cells'],
            'deaths_before_t100': db['100'][0], 'births_t30_100': db['100'][1] - db['30'][1],
            'tick1_refill_share': round(f.get('us_t1', 0) / t1, 3) if t1 else None, 'moves': r['moves'],
            'near_splits': r.get('split_calls_near', 0), 'kids_near_armed': ka, 'kids_near_unarmed': ku,
            'armed_share_of_near_kids': round(ka / (ka + ku), 3) if ka + ku else None,
            'kid_alive10_armed': round(r.get('kids_alive10_a', 0) / ka, 3) if ka else None,
            'kid_alive10_unarmed': round(r.get('kids_alive10_u', 0) / ku, 3) if ku else None,
            'kid_first_bite_armed': round(r.get('kid_first_bite_a', 0) / ka, 3) if ka else None,
            'kid_first_bite_unarmed': round(r.get('kid_first_bite_u', 0) / ku, 3) if ku else None,
            'parent_fired_child_slot': r.get('parent_fired_child_slot', 0),
            'idle_5_15': r.get('idle_5_15', 0), 'front_5_15': r.get('front_5_15', 0),
            'armed_friend': r.get('armed_friend', 0), 'armed_friend_t120': r.get('armed_friend_t120', 0),
            'armed_friend_on_refill_child': r.get('armed_friend_on_rch', 0),
            'refill_kids': r.get('rch_n', 0), 'refill_kids_alive120': r.get('rch_alive120', 0)}


def play(job):
    return flat(H.play(job))


def med(x):
    return statistics.median(x) if x else None


def summary(rows, ctl, v0):
    out = ['# %s: %s' % (NAME, rows[0]['variant']), '', '8 seeds, 3000 ticks, paired seed and seat. Local engine (our own cells as opponents); says nothing about Siect-F.', '']
    by = {r['seed']: r for r in rows}
    ge = lambda ref: sum(1 for s, r in by.items() if s in ref and r['cells_final'] >= ref[s]['cells_final'])
    out.append('final cells (seed: n): ' + ', '.join('%d:%d' % (s, by[s]['cells_final']) for s in sorted(by)))
    out.append('median final %s; paired >= V0 (m2v0): %s/8; paired >= control (split10): %s/8' % (
        med([r['cells_final'] for r in rows]), ge(v0) if v0 else 'n/a', ge(ctl) if ctl else 'n/a'))
    for k in ('cells_t30', 'cells_t60', 'cells_t100', 'births_t30_100', 'deaths_before_t100', 'idle_5_15', 'armed_friend_t120', 'tick1_refill_share',
              'armed_share_of_near_kids', 'kid_alive10_armed', 'kid_alive10_unarmed', 'kid_first_bite_armed', 'kid_first_bite_unarmed'):
        out.append('median %s: %s' % (k, med([r[k] for r in rows if r[k] is not None])))
    out.append('parent_fired_child_slot total: %d; moves min: %d' % (sum(r['parent_fired_child_slot'] for r in rows), min(r['moves'] for r in rows)))
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stamp', required=True)
    ap.add_argument('--ticks', type=int, default=3000)
    ap.add_argument('--seeds', default='1,2,3,4,5,6,7,8')
    ap.add_argument('--variants', default=','.join(VARIANTS))
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(',')]
    vs = a.variants.split(',')
    log = os.path.join(SHARED, '%s_%s_games.jsonl' % (a.stamp, NAME))
    jobs = [dict(variant=v, seed=s, seat=M.seat_for(s), ticks=a.ticks) for s in seeds for v in vs]
    res = {v: {} for v in vs}
    t0 = time.time()
    with multiprocessing.get_context('spawn').Pool(a.workers) as pool:
        for k, r in enumerate(pool.imap_unordered(play, jobs, chunksize=1), 1):
            with open(log, 'a') as f:
                f.write(json.dumps(r, sort_keys=True) + '\n')
            res[r['variant']][r['seed']] = r
            print('[%d/%d] %s s%d cells %d (%.0fs)' % (k, len(jobs), r['variant'], r['seed'], r['cells_final'], time.time() - t0), flush=True)
            if len(res[r['variant']]) == len(seeds):
                with open(os.path.join(SHARED, '%s_%s_%s_summary.md' % (a.stamp, NAME, r['variant'])), 'w') as f:
                    f.write(summary(list(res[r['variant']].values()), res.get('split10'), res.get('m2v0')))


if __name__ == '__main__':
    main()
