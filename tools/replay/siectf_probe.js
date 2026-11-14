// Misfortune vs Siect-F probe for ONE ladder match. Runs in the browser on any logged-in page of the site.
// Paste the whole file, then run:   await siectfProbe(<match id>)
// Two requests: the match page, then (16 s later) the replay. Read-only. Returns one compact object.
// Colony index = row order of the match page's table (checked on Sandbox 146370: row 1 = colony 0).
// Measures, for Misfortune (M) and CogSpore-Siect-F (S):
//   cells: per colony at t30/60/100/300/1000/final; lead: first tick S leads M by >= 10 cells, and the last
//   tick M was ahead; freed: squares freed by the death of an M or S cell, who occupied each within 5 ticks
//   (M / S / other / empty); front: M cells beside an S cell at tick start, share bitten before acting (and the
//   same for S beside M), split <100 / 100-300 / 300+.

async function siectfProbe(id) {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const page = await (await fetch('/matches/' + id)).text();
  const doc = new DOMParser().parseFromString(page, 'text/html');
  const rows = [...doc.querySelectorAll('table tr')].map(r => r.innerText.replace(/\s+/g, ' ').trim()).filter(t => t && !/^Colony/.test(t));
  const M = rows.findIndex(t => /Misfortune/.test(t)), S = rows.findIndex(t => /Siect-F/.test(t));
  if (M < 0 || S < 0) return { id, error: 'Misfortune or Siect-F not in this match', rows };
  const place = i => rows[i].split(' ').find((w, k) => k > 1 && /^[1-4]$/.test(w));
  await sleep(16000);
  const raw = new Uint8Array(await (await fetch('/api/matches/' + id + '/replay')).arrayBuffer());
  const dv = new DataView(raw.buffer);
  const W = dv.getUint16(8, true), H = dv.getUint16(10, true);
  let p = 4 + 23 + 16;   // magic, <HHHHBHQI header (23 bytes), 16 reserved
  const colOf = {}, sqOf = {}, enOf = {}; let ids = [], loaded = false;
  const D = [[0, -1], [1, 0], [0, 1], [-1, 0]];
  const marks = [30, 60, 100, 300, 1000]; const cells = {}; let lead = null, lastAhead = 0, tick = 0;
  const freed = new Map(); const fr = { M: { M: 0, S: 0, other: 0, empty: 0 }, S: { M: 0, S: 0, other: 0, empty: 0 } };
  const front = {}; const win = t => (t < 100 ? '<100' : t < 300 ? '100-300' : '300+');
  const tag = c => (c === M ? 'M' : c === S ? 'S' : 'other');
  while (p < raw.length) {
    const rt = raw[p]; p++;
    if (rt === 2) {
      const n = dv.getUint32(p + 4, true); p += 8;
      for (let i = 0; i < n; i++) {
        const cid = dv.getUint32(p, true), c = raw[p + 4], x = dv.getUint16(p + 5, true), y = dv.getUint16(p + 7, true), e = raw[p + 9]; p += 10;
        if (!loaded) { ids.push(cid); colOf[cid] = c; sqOf[cid] = y * W + x; enOf[cid] = e; }
      }
      loaded = true;
    } else if (rt === 3) { p += 17; }
    else if (rt === 1) {
      tick = dv.getUint32(p, true); p += 12; const nev = dv.getUint32(p, true); p += 4;
      const grid = new Array(W * H).fill(-1); for (const c of ids) grid[sqOf[c]] = c;
      const near = (c, other) => { const s = sqOf[c], x = s % W, y = (s / W) | 0; return D.some(([dx, dy]) => { const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) return false; const g = grid[ny * W + nx]; return g >= 0 && colOf[g] === other; }); };
      const fM = ids.filter(c => colOf[c] === M && near(c, S)), fS = ids.filter(c => colOf[c] === S && near(c, M));
      const acted = new Set(), bf = new Set(), births = [], dead = new Set();
      const land = (sq, c) => { const f = freed.get(sq); if (f && tick - f.t <= 5) { fr[f.who][tag(c)]++; freed.delete(sq); } };
      for (let i = 0; i < nev; i++) {
        const k = raw[p];
        if (k === 4 || k === 5) { const a = dv.getUint32(p + 1, true), b = dv.getUint32(p + 5, true); p += 10; if (k === 4 && !acted.has(b)) bf.add(b); acted.add(a); }
        else if (k === 1) { const cid = dv.getUint32(p + 1, true), c = raw[p + 5], x = dv.getUint16(p + 6, true), y = dv.getUint16(p + 8, true); p += 11; colOf[cid] = c; sqOf[cid] = y * W + x; births.push(cid); land(y * W + x, c); }
        else if (k === 2) { const cid = dv.getUint32(p + 1, true), x = dv.getUint16(p + 5, true), y = dv.getUint16(p + 7, true); p += 9; sqOf[cid] = y * W + x; acted.add(cid); land(y * W + x, colOf[cid]); }
        else if (k === 3) { const cid = dv.getUint32(p + 1, true); p += 5; dead.add(cid); const w = tag(colOf[cid]); if (w !== 'other') freed.set(sqOf[cid], { t: tick, who: w }); }
        else throw new Error('event ' + k);
      }
      for (const [lab, arr] of [['M', fM], ['S', fS]]) { const kk = lab + ' ' + win(tick); front[kk] = front[kk] || [0, 0]; front[kk][1] += arr.length; front[kk][0] += arr.filter(c => bf.has(c)).length; }
      for (const [sq, f] of freed) if (tick - f.t > 5) { fr[f.who].empty++; freed.delete(sq); }
      const n = dv.getUint32(p, true); p += 4; const en = raw.subarray(p, p + n); p += n;
      ids = ids.filter(i => !dead.has(i)).concat(births.filter(b => !dead.has(b))); ids.forEach((cid, i) => (enOf[cid] = en[i]));
      let m = 0, s = 0; for (const c of ids) { if (colOf[c] === M) m++; else if (colOf[c] === S) s++; }
      if (marks.includes(tick)) cells['t' + tick] = m + '/' + s;
      if (m >= s) lastAhead = tick; if (lead === null && s - m >= 10) lead = tick;
    } else throw new Error('record ' + rt);
  }
  let m = 0, s = 0; for (const c of ids) { if (colOf[c] === M) m++; else if (colOf[c] === S) s++; }
  cells.final = m + '/' + s;
  const pct = v => (v[1] ? (100 * v[0] / v[1]).toFixed(0) + '% of ' + v[1] : '-');
  return { id, places: 'M ' + place(M) + ' / S ' + place(S), cells_M_S: cells, S_leads_by10_at: lead, M_last_ahead: lastAhead,
           freed_M_cell_refilled_by: fr.M, freed_S_cell_refilled_by: fr.S,
           bitten_first: Object.fromEntries(Object.entries(front).sort().map(([k, v]) => [k, pct(v)])) };
}
