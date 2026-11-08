"""Section 8 (matches chosen and why) and section 9 (file index) as markdown. python -I tools/pull2/sec8.py"""
import json, glob, re, os
nm = lambda s: re.sub(r'^\W+\s*', '', s).strip()
WHY = {}
for i in (99211, 99198, 99109, 99021, 98879, 98964, 99273, 99291, 99097, 99074, 99061, 99413, 99420, 99134, 99239, 98983, 98844):
    WHY[i] = 'a: Sprint yardstick (Sprint survived long beside the listed rivals)'
for i in (99324, 99122, 99371, 99119, 99168, 99388):
    WHY[i] = 'b: HammerSpb at its best (' + ('both together' if i in (99324, 99119, 99168, 99388) else 'one of them, large margin') + ')'
for i in (98854, 99304, 99230, 99208, 98843, 98911):
    WHY[i] = 'c: upset of HammerSpb by a pump cell'
for i in (98989, 99082, 99365, 98862):
    WHY[i] = 'd: contested 3-4 way match, candidate for a front that moves late'
for i in (98766, 98790, 98797):
    WHY[i] = 'f: re-download of a first-pull match'
for f in sorted(glob.glob('data/pull2/summaries/[0-9]*.json')):
    d = json.load(open(f, encoding='utf-8')); rows = sorted(d['facts']['rows'], key=lambda r: r['place'])
    print('- **%d** (%s; %d ticks, %s): %s' % (d['id'], WHY.get(d['id'], '?'), d['ticksInReplay'], {1: 'tick limit', 2: 'last colony', 3: 'all dead'}.get(d['end']['reason']),
          ', '.join('%d.%s %d' % (r['place'], nm(r['cell']), r['finalPop']) for r in rows)))
print('\nFILES')
for root in ('data/pull2', 'data/pull2/replays', 'data/pull2/keyframes', 'data/pull2/summaries', 'data/pull2/site', 'tools/pull2'):
    fs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x))]
    print(root, len(fs), 'files', round(sum(os.path.getsize(x) for x in fs) / 1e6, 2), 'MB')
