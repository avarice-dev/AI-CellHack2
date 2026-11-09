"""Engine check against real replays: recorded actions only, no cell code, no rival models.

Each tick of a replay is turned into one action per cell, keyed by the cell's square at the start of the tick, and
ordered by the recorded event order (the engine's order_by_alt count).  Two measures:

  tick: the engine starts every tick from the true state, runs that one tick, and every square is compared with the
        replay's end-of-tick state.  Each differing square is charged to a rule by what the replay shows on it.
  keyframe: the engine starts at a keyframe and runs free to the next one (50 ticks), then squares are compared.

What the replay does not record (tool limits, not engine errors):
  - REST, NOP and failed actions leave no event.  An event-free cell is given REST if its energy shows the +1 and NOP
    if not, so rest income is only tested for a delta that is neither.  A cell that was bitten and shows the +1 is
    given a REST before the bites (the replay cannot place it).
    A killed cell gets that REST when its eaters together gained one energy more than it started with.
  - A split event does not name the parent: it is a same-colony neighbour that has no other action and is not yet
    bitten, preferring one with floor(E/2) = the child's energy.
The stream decoder follows tools/replay/mine.py, whose mine() cannot be reused one tick at a time.

Usage: python -I sim/replay_check.py --pull pull5 [--workers N] [--max-ticks T] [--examples K] [replay ids...]
"""
import collections
import gzip
import multiprocessing
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'replay'))
import engine as E  # noqa: E402
import pulls as P  # noqa: E402
from mine import below_normal  # noqa: E402

LAST = 10 ** 7     # order count of a REST whose place in the tick does not matter
RULES = ('death', 'split', 'bite', 'feed', 'move', 'rest')
BIRTH, EV_MOVE, DEATH, EAT, FEED = 1, 2, 3, 4, 5


def ticks(path):
    """Yield ('start', W, H, cells), ('key', t, cells), ('tick', t, events, energies); cells (id, c, x, y, e)."""
    raw = gzip.decompress(open(path, 'rb').read())
    if raw[:4] != b'CHR2':
        raise ValueError('not a CHR2 replay')
    head = '<HHHHBHQI'
    version, _, W, H = struct.unpack_from(head, raw, 4)[:4]
    if version != 4:
        raise ValueError('only format 4 is handled')
    p = 4 + struct.calcsize(head) + 16
    U32, U2, B, M = struct.Struct('<I'), struct.Struct('<II'), struct.Struct('<IBHHB'), struct.Struct('<IHH')
    first = True
    while p < len(raw):
        rt = raw[p]
        p += 1
        if rt == 2:
            t, n = U2.unpack_from(raw, p)
            p += 8
            cells = [B.unpack_from(raw, p + 10 * i) for i in range(n)]
            p += 10 * n
            if first:
                first = False
                yield ('start', W, H, cells)
            else:
                yield ('key', t, cells)
        elif rt == 1:
            t = U32.unpack_from(raw, p)[0]
            p += 12
            nev = U32.unpack_from(raw, p)[0]
            p += 4
            ev = []
            for _ in range(nev):
                k = raw[p]
                if k == EAT or k == FEED:
                    a, b = U2.unpack_from(raw, p + 1)
                    p += 10
                    ev.append((k, a, b))
                elif k == BIRTH:
                    ev.append((k,) + B.unpack_from(raw, p + 1))
                    p += 11
                elif k == EV_MOVE:
                    ev.append((k,) + M.unpack_from(raw, p + 1))
                    p += 9
                elif k == DEATH:
                    ev.append((k, U32.unpack_from(raw, p + 1)[0]))
                    p += 5
                else:
                    raise ValueError('bad event %d' % k)
            n = U32.unpack_from(raw, p)[0]
            p += 4
            yield ('tick', t, ev, raw[p:p + n])
            p += n
        elif rt == 3:
            p += 17
        else:
            raise ValueError('bad record %d' % rt)


def direction(W, s, d):
    """Engine direction from square s to neighbour d, or None if not adjacent."""
    delta = d - s
    if delta == -W:
        return E.DIR_UP
    if delta == 1 and d % W:
        return E.DIR_RIGHT
    if delta == W:
        return E.DIR_DOWN
    if delta == -1 and s % W:
        return E.DIR_LEFT
    return None


class State(object):
    """True board at the start of a tick (viewer order), and the plan of one tick."""

    def __init__(self, W, H, cells):
        self.W, self.H = W, H
        self.ids = [c[0] for c in cells]
        self.col = {c[0]: c[1] for c in cells}
        self.sq = {c[0]: c[3] * W + c[2] for c in cells}
        self.en = {c[0]: c[4] for c in cells}

    def board(self):
        return {self.sq[i]: (self.col[i], self.en[i]) for i in self.ids}

    def parents(self, events, actors, end):
        """Birth id -> parent id.  Matching, the parents whose energy fits exactly first."""
        W, sq, col = self.W, self.sq, self.col
        at = {sq[i]: i for i in self.ids}
        strict, loose = {}, {}
        flows = collections.defaultdict(list)     # non-actor id -> [(event index, energy change)]
        for j, ev in enumerate(events):
            if ev[0] == EAT:
                flows[ev[2]].append((j, -E.EAT_TAKE))
            elif ev[0] == FEED:
                flows[ev[2]].append((j, E.FEED_AMOUNT))
        for j, ev in enumerate(events):
            if ev[0] != BIRTH:
                continue
            cid, c, x, y, e = ev[1:]
            s = y * W + x
            near = (s - W, s + 1 if (s + 1) % W else -1, s + W, s - 1 if s % W else -1)
            opts = [at[p] for p in near if p in at and col[at[p]] == c and at[p] not in actors]
            loose[cid] = opts
            fits = []
            for i in opts:
                before = self.en[i] + sum(d for k, d in flows[i] if k < j)
                after = min(E.ENERGY_MAX, self.en[i] + sum(d for _, d in flows[i]) - e)
                if before // 2 == e and before >= E.SPLIT_MIN and end.get(i, after) == after:
                    fits.append(i)
            strict[cid] = fits
        owner = {}

        def place(b, edges, seen):
            for i in edges[b]:
                if i not in seen:
                    seen.add(i)
                    if i not in owner or place(owner[i], edges, seen):
                        owner[i] = b
                        return True
            return False

        for b in strict:
            place(b, strict, set())
        done = set(owner.values())
        for b in loose:
            if b not in done:
                place(b, loose, set())
        return {b: i for i, b in owner.items()}

    def plan(self, events, energies, stats):
        """Apply one tick.  Returns (plan {(x, y): (action, 0, order)}, tags {square: set of rule names}, contact)."""
        W = self.W
        sq, col = self.sq, self.col
        cur = dict(self.en)                # energy during the tick, from the events
        at = {sq[i]: i for i in self.ids}  # square -> id; a corpse holds its square until the end of the tick
        start = dict(sq)
        actors = set()
        for ev in events:
            if ev[0] == EAT or ev[0] == FEED or ev[0] == EV_MOVE:
                actors.add(ev[1])
        all_dead = set(ev[1] for ev in events if ev[0] == DEATH)
        all_births = [ev[1] for ev in events if ev[0] == BIRTH]
        order_end = [i for i in self.ids if i not in all_dead] + [b for b in all_births if b not in all_dead]
        if len(order_end) != len(energies):
            raise ValueError('cell count differs from the energy record')
        end = dict(zip(order_end, energies))
        plan, tags = {}, collections.defaultdict(set)
        bitten, dead, births = set(), set(), []
        parents = self.parents(events, actors, end)
        fed, bites, eaters = collections.Counter(), collections.Counter(), collections.defaultdict(list)
        for ev in events:
            if ev[0] == EAT:
                bites[ev[2]] += 1
                eaters[ev[2]].append(ev[1])
            elif ev[0] == FEED:
                fed[ev[2]] += 1
        contact = False

        def act(i, base, target, order):
            d = direction(W, sq[i], target)
            if d is None:
                stats['tool: not adjacent'] += 1
                return
            s = start[i]
            plan[(s % W, s // W)] = (base + d, 0, order)

        for n, ev in enumerate(events):
            k = ev[0]
            order = n + 1
            if k == EAT or k == FEED:
                a, b = ev[1], ev[2]
                if a in bitten:
                    stats['real: acted after being bitten'] += 1
                stats['actions'] += 1
                if k == EAT:
                    act(a, E.ACT_EAT, sq[b], order)
                    take = min(E.EAT_TAKE, cur[b])
                    cur[b] -= take
                    cur[a] += take
                    bitten.add(b)
                    if col[a] != col[b]:
                        contact = True
                    rule = 'bite'
                else:
                    act(a, E.ACT_FEED, sq[b], order)
                    give = min(E.FEED_AMOUNT, cur[a])
                    cur[a] -= give
                    cur[b] += give
                    rule = 'feed'
                tags[sq[a]].add(rule)
                tags[sq[b]].add(rule)
            elif k == EV_MOVE:
                i, x, y = ev[1:]
                s, d = sq[i], y * W + x
                if i in bitten:
                    stats['real: acted after being bitten'] += 1
                act(i, E.ACT_MOVE, d, order)
                if at.get(s) == i:
                    del at[s]
                at[d] = i
                sq[i] = d
                tags[s].add('move')
                tags[d].add('move')
            elif k == BIRTH:
                cid, c, x, y, e = ev[1:]
                s = y * W + x
                col[cid] = c
                i = parents.get(cid)
                pick = [i] if i is not None else []
                exact = pick if pick and cur[pick[0]] // 2 == e and cur[pick[0]] >= E.SPLIT_MIN else []
                if not pick:
                    stats['tool: split without a parent'] += 1
                else:
                    if not exact:
                        stats['tool: split parent energy not floor(E/2)'] += 1
                    i = pick[0]
                    actors.add(i)
                    act(i, E.ACT_SPLIT, s, order)
                    cur[i] -= e
                    tags[sq[i]].add('split')
                sq[cid] = s
                cur[cid] = e
                at[s] = cid
                births.append(cid)
                tags[s].add('split')
            else:  # DEATH: the corpse keeps its square until the end of the tick
                dead.add(ev[1])
                tags[sq[ev[1]]].add('death')

        for i in self.ids:                 # event-free actions, from the energy delta
            if i in actors or i in dead:
                continue
            s = start[i]
            without = min(E.ENERGY_MAX, cur[i])
            if end[i] != without and end[i] == min(E.ENERGY_MAX, cur[i] + 1):
                plan[(s % W, s // W)] = (E.ACT_REST, 0, 0 if i in bitten else LAST)
                stats['rest before a bite (bitten, shows +1)' if i in bitten else 'rest (+1 seen)'] += 1
            elif end[i] == without:
                stats['stunned or no gain (bitten)' if i in bitten else 'no +1 (NOP or failed action)'] += 1
            elif end[i] != without:
                plan[(s % W, s // W)] = (E.ACT_REST, 0, 0 if i in bitten else LAST)  # shows up in the diff
        for i in dead:                     # a killed cell that rested first gave its eaters one energy more
            if i in actors or i not in self.en or i not in bitten or fed[i]:
                continue
            gains = [end[a] - self.en[a] - 2 * fed[a] + 2 * bites[a] if a in end and end[a] < E.ENERGY_MAX else None
                     for a in eaters[i]]
            if None not in gains and sum(gains) == self.en[i] + 1:
                s = start[i]
                plan[(s % W, s // W)] = (E.ACT_REST, 0, 0)
                stats['rest before a killing bite (eater gains)'] += 1
        for i in dead:
            sq.pop(i, None)
        self.ids = order_end
        self.en = end
        return plan, tags, contact


def new_engine(state, plan_box):
    def policy(v, _mem):
        return plan_box[0].get((v.x, v.y), (E.ACT_NOP, 0, 0))
    eng = E.Engine([policy] * 4, width=state.W, height=state.H, max_ticks=10 ** 9, place_start=False,
                   order_by_alt=True)
    eng.present = [True] * 4
    for i in state.ids:
        eng.add_cell(state.sq[i] % state.W, state.sq[i] // state.W, state.col[i], state.en[i])
    return eng


def engine_board(eng):
    return {y * eng.W + x: (c, e) for _, x, y, c, e in eng.cells()}


def rule_of(tag_set):
    for r in RULES:
        if r in tag_set:
            return r
    return 'rest'


def check(args):
    pull, rid, max_ticks, keep = args
    below_normal()
    path = P.pull_dir(pull, 'replays', '%s.chr2.gz' % rid)
    state = None
    box = [{}]
    stats = collections.Counter()
    per = collections.Counter()      # (phase, measure or rule)
    examples = {}
    contact_seen = False
    eng = free = None
    for rec in ticks(path):
        if rec[0] == 'start':
            state = State(rec[1], rec[2], rec[3])
            eng = new_engine(state, box)
            free = new_engine(state, box)
            continue
        if rec[0] == 'key':
            t = rec[1]
            if t and contact_seen is not None and free is not None:
                real = state.board()
                got = engine_board(free)
                phase = 'post' if contact_seen else 'pre'
                per[(phase, 'kf squares')] += len(set(real) | set(got))
                per[(phase, 'kf differ')] += sum(1 for s in set(real) | set(got) if real.get(s) != got.get(s))
                per[(phase, 'kf owner differ')] += sum(1 for s in set(real) | set(got)
                                                       if (real.get(s) or (None,))[0] != (got.get(s) or (None,))[0])
            free = new_engine(state, box)
            free.tick = t
            continue
        t, events, energies = rec[1:]
        if t >= max_ticks:
            break
        plan, tags, contact = state.plan(events, energies, stats)
        box[0] = plan
        eng.tick = t
        eng.finished = False
        eng.step()
        free.finished = False
        free.step()
        contact_seen = contact_seen or contact
        phase = 'post' if contact_seen else 'pre'
        real = state.board()
        got = engine_board(eng)
        per[(phase, 'squares')] += len(set(real) | set(got))
        for s in set(real) | set(got):
            a, b = real.get(s), got.get(s)
            if a == b:
                continue
            structural = a is None or b is None or a[0] != b[0]
            rule = rule_of(tags.get(s, ()))
            per[(phase, rule)] += 1
            per[(phase, 'differ')] += 1
            if len(examples.setdefault(rule, [])) < keep:
                examples[rule].append((rid, t, s % state.W, s // state.W, 'real', a, 'engine', b,
                                       sorted(tags.get(s, ())), 'owner' if structural else 'energy'))
        if real != got:
            eng = new_engine(state, box)   # back to the true state
    return rid, per, stats, examples


def main():
    pull, rest = P.take_pull(sys.argv[1:], 'replay_check.py')
    workers, max_ticks, keep, ids = 4, 10 ** 9, 3, []
    i = 0
    while i < len(rest):
        if rest[i] == '--workers':
            workers = min(4, int(rest[i + 1]))
            i += 2
        elif rest[i] == '--max-ticks':
            max_ticks = int(rest[i + 1])
            i += 2
        elif rest[i] == '--examples':
            keep = int(rest[i + 1])
            i += 2
        else:
            ids.append(rest[i])
            i += 1
    if not ids:
        ids = sorted(f.split('.')[0] for f in os.listdir(P.pull_dir(pull, 'replays')))[:3]
    below_normal()
    jobs = [(pull, r, max_ticks, keep) for r in ids]
    with multiprocessing.Pool(min(workers, len(jobs))) as pool:
        results = pool.map(check, jobs)
    per, stats, ex = collections.Counter(), collections.Counter(), {}
    for rid, p, s, e in results:
        per.update(p)
        stats.update(s)
        for k, v in e.items():
            ex.setdefault(k, []).extend(v)
    for phase in ('pre', 'post'):
        n = per[(phase, 'squares')]
        print('%s contact: %d squares compared tick by tick, %d differ (%.4f%%)' %
              (phase, n, per[(phase, 'differ')], 100.0 * per[(phase, 'differ')] / max(n, 1)))
        print('   by rule: ' + ', '.join('%s %d' % (r, per[(phase, r)]) for r in RULES))
        m = per[(phase, 'kf squares')]
        print('   keyframe free run (50 ticks): %d squares, %d differ (%.2f%%), owner differs %d (%.2f%%)' %
              (m, per[(phase, 'kf differ')], 100.0 * per[(phase, 'kf differ')] / max(m, 1),
               per[(phase, 'kf owner differ')], 100.0 * per[(phase, 'kf owner differ')] / max(m, 1)))
    print('notes: ' + (', '.join('%s %d' % kv for kv in sorted(stats.items())) or 'none'))
    for r in RULES:
        for row in ex.get(r, []):
            print(r, row)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
