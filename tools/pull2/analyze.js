/* CellHack2 pull 2: in-page replay analysis. Paste into the match-site page (needs window.CellHackViewer from
   /static/viewer.js and window.saveBlob). Defines window.P2 = { pull(id, names, facts), analyze(dec, names, facts) }.
   Conventions: UP = target y < eater y (y grows downward on the board); RIGHT = target x > eater x.
   Colony index c = index in the match (0..3). Energies are raw replay units (u8).
   Bite order (see report): for each eat by colony A in direction d, and each other colony B that has >= 1 eat in the
   same tick: pre = A's eat precedes ALL of B's eats that tick; post = follows ALL; mix = in between (then
   mixFirst += 1 if fewer B eats came before it than after, 0.5 if equal). %first = (pre + mixFirst) / n. */
(function () {
  const NMAX = 1 << 22;
  const dirOf = (ex, ey, tx, ty) => { const dx = tx - ex, dy = ty - ey;
    if (dx === 0 && dy < 0) return 0; if (dy === 0 && dx > 0) return 1; if (dx === 0 && dy > 0) return 2; if (dy === 0 && dx < 0) return 3; return 4; };
  const sparse = a => { const o = {}; for (let i = 0; i < a.length; i++) if (a[i]) o[i] = a[i]; return o; };
  const mk = () => [0, 1, 2, 3].map(() => new Float64Array(256));
  const mean = a => a.length ? a.reduce((s, v) => s + v, 0) / a.length : null;

  function analyze(dec, names, facts) {
    const h = dec.h, W = h.w, H = h.h, ticks = dec.ticks, T = ticks.length, kf = dec.keyframes;
    const kft = Object.keys(kf).map(Number).sort((a, b) => a - b);
    const colOf = new Uint8Array(NMAX).fill(255), X = new Int16Array(NMAX), Y = new Int16Array(NMAX);
    const E = new Int32Array(NMAX), stamp = new Int32Array(NMAX), bornAt = new Int32Array(NMAX).fill(-1);
    const grid = new Int32Array(W * H);                       // id+1 or 0
    const st = new CellHackViewer.State(); st.load(kf[0]);
    for (const c of kf[0]) { colOf[c.id] = c.c; X[c.id] = c.x; Y[c.id] = c.y; E[c.id] = c.e; grid[c.y * W + c.x] = c.id + 1; }
    const tot = [0, 1, 2, 3].map(() => ({ births: 0, moves: 0, deaths: 0, eatsEnemy: 0, eatsFriend: 0, feeds: 0, eatAmt: 0, feedAmt: 0 }));
    const eatHist = mk(), feedHist = mk(), feederB = mk(), recvB = mk(), parentB = mk(), childE = mk(), parentA = mk();
    const triples = [{}, {}, {}, {}], ambiguous = [0, 0, 0, 0], attributed = [0, 0, 0, 0];
    const bite = {};  // "A>B" -> dir -> {n,pre,post,mix,mixFirst}
    const biteRec = (a, b, d) => { const k = a + '>' + b; const o = bite[k] || (bite[k] = {}); const dn = d === 4 ? 'OTHER' : ['UP', 'RIGHT', 'DOWN', 'LEFT'][d];
      return o[dn] || (o[dn] = { n: 0, pre: 0, post: 0, mix: 0, mixFirst: 0 }); };
    const pops = new Int32Array(T * 4);
    const val = { kfChecked: 0, kfMismatch: 0, cellsChecked: 0, uninvolvedMismatch: 0, involvedMismatch: 0, involvedChecked: 0, eatTargetNotDead: 0, eatTargetDead: 0, diagEats: 0, firstMismatches: [] };
    const eatMode = { selfPlusAmt: 0, other: 0 };
    let evCount = 0; const cnt=new Int8Array(NMAX), role=new Int8Array(NMAX), pre=new Int32Array(NMAX), st2=new Int32Array(NMAX); const dh=[0,1,2,3,4,5].map(()=>new Float64Array(201)); const touch=(id,r,stp)=>{ if(st2[id]!==stp){st2[id]=stp;cnt[id]=0;pre[id]=E[id];} cnt[id]++; role[id]=r; };  // DIAG: per-role energy delta histogram (0 untouched, 1 eater, 2 target, 3 feeder, 4 receiver, 5 several events)
    for (let t = 0; t < T; t++) {
      const rec = ticks[t]; if (!rec) continue;
      pops.set(rec.pop, t * 4);
      if (t > 0 && kf[t]) {   // start-of-tick state must equal keyframe t
        val.kfChecked++;
        const a = st.cells, b = kf[t]; let bad = a.length !== b.length;
        if (!bad) for (let i = 0; i < a.length; i++) { const p = a[i], q = b[i]; if (p.id !== q.id || p.c !== q.c || p.x !== q.x || p.y !== q.y || p.e !== q.e) { bad = true; break; } }
        if (bad) val.kfMismatch++;
      }
      const evs = rec.events, stp = t + 1, eats = [], births = [], deadNow = [];
      for (let i = 0; i < evs.length; i++) {
        const ev = evs[i], k = ev.k; evCount++;
        if (k === 5) {
          const c = colOf[ev.id]; tot[c].feeds++; tot[c].feedAmt += ev.amt; feedHist[c][ev.amt]++;
          touch(ev.id,3,stp); touch(ev.id2,4,stp); feederB[c][Math.min(255, Math.max(0, E[ev.id]))]++; recvB[c][Math.min(255, Math.max(0, E[ev.id2]))]++;
          E[ev.id] -= ev.amt; E[ev.id2] += ev.amt; stamp[ev.id] = stp; stamp[ev.id2] = stp;
        } else if (k === 4) {
          const ce = colOf[ev.id], ct = colOf[ev.id2];
          if (ce === ct) tot[ce].eatsFriend++; else tot[ce].eatsEnemy++;
          tot[ce].eatAmt += ev.amt; eatHist[ce][ev.amt]++;
          const d = dirOf(X[ev.id], Y[ev.id], X[ev.id2], Y[ev.id2]); if (d === 4) val.diagEats++;
          eats.push(ce, ct, d); touch(ev.id,1,stp); touch(ev.id2,2,stp);
          E[ev.id] += ev.amt; stamp[ev.id] = stp; stamp[ev.id2] = stp;
        } else if (k === 1) {
          colOf[ev.id] = ev.c; X[ev.id] = ev.x; Y[ev.id] = ev.y; E[ev.id] = ev.e; bornAt[ev.id] = t; grid[ev.y * W + ev.x] = ev.id + 1;
          tot[ev.c].births++; childE[ev.c][ev.e]++; births.push(ev); stamp[ev.id] = stp;
        } else if (k === 2) {
          const c = colOf[ev.id]; tot[c].moves++; grid[Y[ev.id] * W + X[ev.id]] = 0; X[ev.id] = ev.x; Y[ev.id] = ev.y; grid[ev.y * W + ev.x] = ev.id + 1; stamp[ev.id] = stp;
        } else if (k === 3) {
          const c = colOf[ev.id]; tot[c].deaths++; if (grid[Y[ev.id] * W + X[ev.id]] === ev.id + 1) grid[Y[ev.id] * W + X[ev.id]] = 0; stamp[ev.id] = stp; deadNow.push(ev.id);
        }
      }
      // bite order within the tick (eats is a flat list of triples ce, ct, d in event order)
      const TB = [0, 0, 0, 0], S = [0, 0, 0, 0];
      for (let i = 0; i < eats.length; i += 3) TB[eats[i]]++;
      for (let i = 0; i < eats.length; i += 3) {
        const a = eats[i], d = eats[i + 2];
        for (let b = 0; b < 4; b++) {
          if (b === a || TB[b] === 0) continue;
          const r = biteRec(a, b, d), bb = S[b], aa = TB[b] - S[b]; r.n++;
          if (bb === 0) r.pre++; else if (aa === 0) r.post++; else { r.mix++; r.mixFirst += bb < aa ? 1 : bb === aa ? 0.5 : 0; }
        }
        S[a]++;
      }
      st.apply(rec);
      // authoritative energies vs the model; parent attribution for births
      const cells = st.cells, idx = st.index;
      for (let i = 0; i < cells.length; i++) {
        const c = cells[i], inv = stamp[c.id] === stp;
        if (E[c.id] !== c.e) { if (inv) val.involvedMismatch++; else { val.uninvolvedMismatch++; if (val.firstMismatches.length < 8) val.firstMismatches.push([t, c.id, E[c.id], c.e]); } }
        if (inv) val.involvedChecked++; { const r = (st2[c.id] === stp && cnt[c.id] === 1) ? role[c.id] : (st2[c.id] === stp ? 5 : 0); const base = (st2[c.id] === stp) ? pre[c.id] : E[c.id]; dh[r][Math.max(0, Math.min(200, c.e - base + 100))]++; }
        val.cellsChecked++;
      }
      for (const b of births) {
        const nb = [[b.x + 1, b.y], [b.x - 1, b.y], [b.x, b.y + 1], [b.x, b.y - 1]], cand = [];
        for (const [nx, ny] of nb) {
          if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
          const g = grid[ny * W + nx] - 1; if (g < 0 || colOf[g] !== b.c || bornAt[g] === t || stamp[g] === stp) continue;
          const j = idx.get(g); if (j === undefined) continue; const after = cells[j].e;
          if (E[g] > after) cand.push([E[g], after]);
        }
        if (cand.length === 1) { attributed[b.c]++; parentB[b.c][Math.min(255, cand[0][0])]++; parentA[b.c][cand[0][1]]++;
          const key = cand[0][0] + ',' + b.e + ',' + cand[0][1]; triples[b.c][key] = (triples[b.c][key] || 0) + 1; }
        else ambiguous[b.c]++;
      }
      for (let i = 0; i < cells.length; i++) E[cells[i].id] = cells[i].e;
    }
    // ---- per-keyframe stats
    const meanE = {}, fi = {};
    for (const t of kft) {
      const per = [[], [], [], []]; for (const c of kf[t]) per[c.c].push(c.e);
      meanE[t] = per.map(a => { const m = mean(a); return m === null ? null : +m.toFixed(3); });
      if ([200, 500, 1000, 2000].includes(t)) {
        const g = new Int32Array(W * H).fill(-1); for (const c of kf[t]) g[c.y * W + c.x] = c.c;
        const f = [[], [], [], []], it = [[], [], [], []];
        for (const c of kf[t]) { let front = false;
          for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const nx = c.x + dx, ny = c.y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue; const o = g[ny * W + nx]; if (o >= 0 && o !== c.c) { front = true; break; } }
          (front ? f : it)[c.c].push(c.e); }
        fi[t] = [0, 1, 2, 3].map(c => ({ front: { mean: f[c].length ? +mean(f[c]).toFixed(3) : null, n: f[c].length }, interior: { mean: it[c].length ? +mean(it[c]).toFixed(3) : null, n: it[c].length } }));
      }
    }
    const endE = [[], [], [], []]; for (const c of st.cells) endE[c.c].push(c.e);
    meanE.end = endE.map(a => { const m = mean(a); return m === null ? null : +m.toFixed(3); });
    // ---- starts
    const starts = [0, 1, 2, 3].map(c => kf[0].filter(x => x.c === c).map(x => ({ x: x.x, y: x.y, e: x.e, nearestEdge: Math.min(x.x, x.y, W - 1 - x.x, H - 1 - x.y) })));
    const pairD = []; for (let a = 0; a < 4; a++) for (let b = a + 1; b < 4; b++) if (starts[a][0] && starts[b][0]) { const p = starts[a][0], q = starts[b][0];
      pairD.push({ a, b, dx: Math.abs(p.x - q.x), dy: Math.abs(p.y - q.y), manhattan: Math.abs(p.x - q.x) + Math.abs(p.y - q.y), euclid: +Math.hypot(p.x - q.x, p.y - q.y).toFixed(1) }); }
    const pop10 = [0, 1, 2, 3].map(c => { const o = []; for (let t = 0; t < T; t += 10) o.push(pops[t * 4 + c]); return o; });
    // ---- freeze tick: earliest t with every colony's later pop within 5% of pop(t)
    let freeze = null; { const mx = [0, 0, 0, 0], mn = [1e9, 1e9, 1e9, 1e9]; let ok = [true, true, true, true]; let best = T;
      for (let t = T - 1; t >= 0; t--) { let all = true; for (let c = 0; c < 4; c++) { const p = pops[t * 4 + c]; mx[c] = Math.max(mx[c], p); mn[c] = Math.min(mn[c], p); if (!(mx[c] <= p * 1.05 && mn[c] >= p * 0.95)) all = false; }
        if (all) best = t; else break; } freeze = best; }
    const fp = c => ({ feedAmtHist: sparse(feedHist[c]), feederEnergyBefore: sparse(feederB[c]), receiverEnergyBefore: sparse(recvB[c]), feedsPerEat: tot[c].eatsEnemy ? +(tot[c].feeds / tot[c].eatsEnemy).toFixed(3) : null });
    const out = {
      id: facts.id, facts, header: { version: h.version, ruleset: h.ruleset, w: W, h: H, maxTicks: h.maxTicks, seed: h.seed, ids: h.ids, energyScale: h.energyScale, kfEvery: h.kf },
      end: dec.end, ticksInReplay: T, events: evCount, names, starts, startPairs: pairD, pop10, popFinal: Array.from(pops.slice((T - 1) * 4, T * 4)),
      totals: tot, meanEnergy: meanE, frontInterior: fi, biteFirst: bite,
      split: [0, 1, 2, 3].map(c => ({ births: tot[c].births, attributed: attributed[c], ambiguous: ambiguous[c], parentBefore: sparse(parentB[c]), childE: sparse(childE[c]), parentAfter: sparse(parentA[c]), triples: triples[c] })),
      feed: [0, 1, 2, 3].map(fp), eatAmtHist: eatHist.map(sparse), freezeTick: freeze, deltaHist: dh.map(a => { const o = {}; for (let i = 0; i < 201; i++) if (a[i]) o[i - 100] = a[i]; return o; }), validation: val
    };
    return out;
  }

  async function gz(obj) { const s = typeof obj === 'string' ? obj : JSON.stringify(obj);
    return await new Response(new Blob([s]).stream().pipeThrough(new CompressionStream('gzip'))).blob(); }

  async function pull(id, names, facts) {
    const r = await fetch('/api/matches/' + id + '/replay', { credentials: 'same-origin' });
    if (r.status !== 200) throw new Error('HTTP ' + r.status + ' replay ' + id);
    let buf = await r.arrayBuffer(); const u = new Uint8Array(buf); const isGz = u[0] === 0x1f && u[1] === 0x8b;
    let rawGz, plain;
    if (isGz) { rawGz = new Blob([buf]); plain = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer(); }
    else { plain = buf; rawGz = await new Response(new Blob([buf]).stream().pipeThrough(new CompressionStream('gzip'))).blob(); }
    buf = null;
    const info = { isGz, rawBytes: plain.byteLength, gzBytes: rawGz.size };
    saveBlob(id + '.chr2.gz', rawGz);
    let dec = CellHackViewer.decode(plain); plain = null;
    const out = analyze(dec, names, facts); out.fetchInfo = info;
    const kfo = { header: out.header, end: dec.end, names, keyframes: {} };
    for (const t of Object.keys(dec.keyframes)) kfo.keyframes[t] = dec.keyframes[t].map(c => [c.id, c.c, c.x, c.y, c.e]);
    const kfb = await gz(kfo); saveBlob(id + '.kf.json.gz', kfb); info.kfGzBytes = kfb.size;
    saveBlob(id + '.json', new Blob([JSON.stringify(out)], { type: 'application/json' }));
    dec = null; return out;
  }
  window.P2 = { pull, analyze, gz };
})();
