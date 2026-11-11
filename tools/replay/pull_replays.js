// Pull match pages and replays from the CellHack2 site.  Runs in the browser, on any page of the site, in a
// session that is logged in.  It does not log in and it reads no account data.
//
// Use:
//   1. Open the site, log in, open the browser console on any page of the site.
//   2. Paste this whole file.
//   3. Run:   pullReplays([103747, 103750])            // match pages and replays
//      or:    pullReplays([103747, 103750], {replays: false})   // match pages only (the match list)
//      Options: replays (default true), source and note (free text for the match list).
//   4. Watch the progress:   pullStatus()
//   5. The browser saves one <id>.chr2.gz for each replay and, at the end, one matches-<time>.json.
//      Move them into the pull:   tools/replay/collect.sh <pull> [downloads folder]
//
// Keep the tab visible: browsers slow the timers of a hidden tab.
//
// Pacing (see "Pacing rules for the site" in architecture/data-pulls.md): one request at a time, pages at least
// 15 seconds apart, replays at least 30 seconds apart, and on HTTP 429 or an error a wait of at least 60 seconds
// that doubles up to 5 minutes.

const PAGE_GAP_MS = 16000;
const REPLAY_GAP_MS = 31000;
const BACKOFF_MS = 60000;
const BACKOFF_MAX_MS = 300000;
const RETRIES = 4;

const pullState = { done: [], errors: [], matches: [], finished: false, started: false };

function pullStatus() {
  return JSON.stringify({ started: pullState.started, finished: pullState.finished, done: pullState.done,
                          errors: pullState.errors, matches: pullState.matches.length });
}

function pullSleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function pullClean(s) {
  return (s || '').replace(/\s+/g, ' ').trim();
}

// One request, with the back-off rule.  Returns the Response, or null after RETRIES failures.
async function pullFetch(url, what) {
  let wait = BACKOFF_MS;
  for (let attempt = 0; attempt < RETRIES; attempt++) {
    try {
      const r = await fetch(url);
      if (r.ok) return r;
      pullState.errors.push(what + ': HTTP ' + r.status);
    } catch (e) {
      pullState.errors.push(what + ': ' + e.message);
    }
    await pullSleep(wait);
    wait = Math.min(wait * 2, BACKOFF_MAX_MS);
  }
  return null;
}

// The match page table: one row per colony, in the replay's colony order.  The first cell of a row is an empty
// colour swatch, so the nine values are the LAST nine cells: name, player, place, final population, peak,
// energy, faults, instructions "average (maximum)", rating "before -> after" (empty for Sandbox games).
function pullMatchFromPage(id, html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const rows = Array.from(doc.querySelectorAll('table tr'))
    .map(tr => Array.from(tr.querySelectorAll('td')).map(td => pullClean(td.textContent)))
    .filter(cells => cells.length >= 9)
    .map(cells => cells.slice(-9));
  const colonies = rows.map(c => ({ name: c[0], player: c[1], place: c[2], pop: c[3], peak: c[4], energy: c[5],
                                    faults: c[6], insns: c[7], rating: c[8] }));
  const first = colonies.find(c => c.place === '1');
  return { id: id, cells: colonies.map(c => c.name), winner: first ? first.name : '', colonies: colonies };
}

function pullSave(blob, filename) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// The site sends the replay compressed and the browser unpacks it.  The tools read gzip files, so pack it again.
async function pullGzip(buffer) {
  const bytes = new Uint8Array(buffer);
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) return new Blob([buffer]);
  return await new Response(new Blob([buffer]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
}

async function pullReplays(ids, opt) {
  opt = opt || {};
  const wantReplays = opt.replays !== false;
  pullState.done = []; pullState.errors = []; pullState.matches = []; pullState.finished = false;
  pullState.started = true;
  for (const id of ids) {
    await pullSleep(PAGE_GAP_MS);
    const page = await pullFetch('/matches/' + id, id + ' page');
    if (page) pullState.matches.push(pullMatchFromPage(id, await page.text()));
    if (wantReplays) {
      await pullSleep(REPLAY_GAP_MS);
      const replay = await pullFetch('/api/matches/' + id + '/replay', id + ' replay');
      if (replay) pullSave(await pullGzip(await replay.arrayBuffer()), id + '.chr2.gz');
    }
    pullState.done.push(id);
  }
  const list = { utc: new Date().toISOString(), source: opt.source || 'match pages read by tools/replay/pull_replays.js',
                 note: opt.note || '', matches: pullState.matches };
  const stamp = list.utc.slice(0, 19).replace(/:/g, '-');
  pullSave(new Blob([JSON.stringify(list, null, 1) + '\n'], { type: 'application/json' }), 'matches-' + stamp + '.json');
  pullState.finished = true;
  return pullStatus();
}
