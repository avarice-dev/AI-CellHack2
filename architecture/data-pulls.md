# Data pulls and replay tools

The project studies real games from the public CellHack2 site. The site serves each match's replay as a separate file. So the project collects the match lists, match pages and replays in rounds called **pulls**. It then decodes the replays and turns them into tables and write-ups. This document explains what each pull collected, how the replays are read, where the files are, and the rules the project follows when it fetches data.

## The four pulls

All four pulls were collected on 2026-11-08.

| Pull | What it collected | Main write-up |
|---|---|---|
| 1 | 10 match-list pages (398 finished ladder matches, ids 98432 to 98829), 13 replays, a few match pages, and the leaderboard. | `data/ladder-data-2026-11-08.md` |
| 2 | 16 match-list pages (593 finished ladder matches, ids 98830 to 99422), 165 small match pages, the leaderboard, and 36 replays. 35 raw replay files were kept. | `data/ladder-data-2-2026-11-08.md` |
| 3 | The newest 100 finished ladder games of the Scourge cell (matches 103128 to 103747), one match page for each, and 15 replays of games Scourge lost. | `data/scourge-losses-2026-11-08.md` |
| 4 | All 95 finished ladder games of the Contagion cell (matches 103614 to 104195), and 12 replays (6 wins, 6 losses). | `data/contagion-games-2026-11-08.md` |

Pull 1 and pull 2 were read through a logged-in browser session. Pull 3 and pull 4 used the site's match list and match pages. The offline study of the 35 pull 2 replays is in `data/replay-mining-2026-11-08.md`. Site mechanics and calibration results are in `data/site-observations-2026-11-08.md`. Ratings logged over time are in `data/site-checks.md`.

## What the site gives

| Item | What it contains |
|---|---|
| Leaderboard | For each cell: rating, games, wins, average place and average instructions per call. |
| Match list | The finished matches for a cell or for the whole ladder. |
| Match page | For each colony: player, place, final population, peak population, energy, faults, instructions per call (average and maximum), and the rating before and after the match. |
| Replay | The full record of one match, as a gzip-compressed binary file of the form `CHR2`. Pull 2 notes that later 3000-tick replays were 25 to 53 MB gzipped each. |

## How a replay is read

A replay is a binary stream. The site's own page decodes it with a function called `CellHackViewer.decode`. The decoded data has these parts:

- **Header.** Format version 4, ruleset 9, a 64 by 64 board, 3000 ticks, the seed, the colony ids, and a keyframe every 50 ticks.
- **Keyframes.** A full list of the living cells every 50 ticks: id, colony, position and energy.
- **Ticks.** For each tick, the population of each colony, the energy of every cell, and the list of events.
- **Events.** Five kinds: a birth (k1), a move (k2), a death (k3), an eat (k4) and a feed (k5).
- **End.** The final placement, the populations, the reason the match ended, and the number of ticks run.

Events within a tick are listed in turn order. This lets the studies measure which colony acted first.

The replays do not log every action. A cell that rests produces no event, so it looks like a cell with no event at all. A split parent produces no event either. Only the child is logged. The mining write-up notes both points, and the design notes also record that replays do not log rests.

## The decoder

`tools/pull2/mine.py` is a pure Python version of the site's decoder. It reads one replay at a time and streams it tick by tick. It has two checks built in. It compares the state at the start of each tick with the keyframes in the file. It also checks that the count of energy values matches the count of living cells.

The check passed for all 35 replays in pull 2. The modelled state matched all 1732 keyframes with no mismatches. Pull 3 and pull 4 reported 0 keyframe mismatches as well.

The decoder runs in about 2 to 8 seconds per replay, on one process at below-normal priority.

`mine.py` runs two analyses:

- **Refill race.** For every death, it records which colony took the freed square, how many ticks later, and the energy of the new cell. It also records which colonies were next to the square when the cell died.
- **Resting income.** For every cell and tick with no event, it records the energy change. This shows how much a cell gains from resting, by its starting energy.

## Layout of the data folder

The data folder is organised by pull. Repository-relative paths only.

```
data/
  *.md                              write-ups for each pull and study, plus site notes
  site-checks.md                    ratings logged at several times
  pull2/
    matches-98830-99422.json        the match list (593 matches)
    leaderboard-*.json              leaderboard snapshot
    sprint-match-pages.json         small match pages, the Sprint set
    other-match-pages.json          small match pages, the other set
    winrates.json                   win rate data (see lists.py)
    validation-table.md             table read by sim/validate.py
    site/viewer.js                  copy of the site's replay decoder
    replays/<id>.chr2.gz            raw replays (35 kept)
    keyframes/<id>.kf.json.gz       keyframes for each replay
    summaries/<id>.json             one summary per replay
    mining/                         output of mine.py and mine_report.py
  pull3/ and pull4/
    matches-*.json, names.json      match lists and name tables
    replays/                        raw replays; git-ignored (too large for the repo)
    mining/<id>.json                per-game timelines
    mining/races/<id>.csv.gz        one row per death (refill race)
```

## Tools

Run each tool from the repository root. Most read files with paths that start with `data/`.

| Tool | What it does |
|---|---|
| `tools/pull2/mine.py` | The decoder and the two analyses. Run `python -I tools/pull2/mine.py [replay ids]`. Set the environment variable `CH_PULL` to `pull3` or `pull4` to read another pull. |
| `tools/pull2/mine_report.py` | Combines the mining output by cell name into tables. Run `python -I tools/pull2/mine_report.py`. |
| `tools/pull2/actions.py` | Shows, for one replay, what each cell did when an enemy was next to it. |
| `tools/pull2/analyze.js` | The browser-side analyzer used in pull 2. It ran inside the replay page. |
| `tools/pull2/report.py` | Builds summary tables from the summaries. |
| `tools/pull2/lists.py` | Win rates and head-to-heads from the match lists. |
| `tools/pull2/select_sprint.py` | Lists matches with Sprint, and how Sprint fared in each. |
| `tools/pull2/late.py` | Finds the largest population changes after tick 500, and the freeze tick of each match. |
| `tools/pull2/sec8.py` | Builds the table of matches chosen for study and why. |
| `tools/pull2/collect.sh` | Moves finished files saved by the browser into `data/pull2/`. It removes the number the browser adds to a repeated file name, so the newer copy replaces the older one. It takes an optional folder argument. |
| `tools/pull3/tab.py` | Builds the table of Scourge games. It also writes `data/pull3/names.json`. |
| `tools/pull3/losses.py` | Builds a timeline for each game Scourge lost. |
| `tools/pull4/tab.py` | Builds the table of Contagion games, with a Contagion against Scourge comparison. |
| `tools/pull4/games.py` | Builds a timeline for each Contagion game. |
| `tools/privacy_check.py` | Looks for local paths and personal text in the files. |

## Pacing rules for the site

The project keeps its requests to the site slow. It follows these rules, which come from the pull write-ups and the decision records.

1. **Check the small pages first.** Read the leaderboard, a small page, before fetching large files. This shows whether the rival cells changed version.
2. **Wait between replay fetches.** Pull 1 fetched replays 12 to 20 seconds apart. Pull 2 waited 17 seconds, and later 8 seconds, after the owner allowed a faster pace. Pull 3 waited 6 seconds between match pages. Pull 2 recorded no HTTP errors, no 429 responses and no 5xx responses.
3. **Create cells slowly.** The site limits how often a cell can be created. Two requests 4 seconds apart got HTTP 429. Two requests 30 seconds apart worked.
4. **Leave a gap between Sandbox runs.** The Sandbox refused runs made 10 seconds apart, with the message "please wait 5s". The site notes say runs need about 15 seconds between them.
5. **Use stored data before fetching more.** Decision G18 accepts offline re-analysis of stored replays only, with no new fetches. The reason recorded is that the site is fetched gently and the data is already on disk.
6. **Keep each fetch small.** Pull 2 deleted one raw replay to keep the data under the size cap. Its keyframes and summary were kept. The write-up does not give the size cap.

The simulator has its own limit on local load. It uses at most four worker processes. See [simulator.md](simulator.md).

## Pitfalls for new readers

- **Rests are not logged.** A cell that rests produces no event. Resting income is therefore measured from the cells that had no event.
- **Splits show only the child.** A splitting parent appears as an event-free cell with a negative energy change.
- **Energy is read at the end of a tick.** The energy values in the tick records are the values at the end of the tick.
- **Facts from one pull may not hold for another.** Each write-up states the match ids and dates it covers.

## Related documents

- `data/ladder-data-2-2026-11-08.md`: the main study of pull 2, with its headline findings and rival profiles.
- `data/replay-mining-2026-11-08.md`: the refill race and resting income, from the 35 pull 2 replays.
- [cells-and-experiments.md](cells-and-experiments.md): how these findings became cell designs.
