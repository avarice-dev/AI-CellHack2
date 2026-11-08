# Data pulls and replay tools

The project studies real games from the public CellHack2 site. The site serves each match's replay as a separate file. So the project collects the match lists, match pages and replays in rounds called **pulls**. It then decodes the replays and turns them into tables and write-ups. This document explains what each pull collected, how the replays are read, where the files are, and the rules the project follows when it fetches data.

## The pulls

All five pulls were collected on 2026-11-08.

| Pull | What it collected | Main write-up |
|---|---|---|
| 1 | 10 match-list pages (398 finished ladder matches, ids 98432 to 98829), 13 replays, a few match pages, and the leaderboard. | `data/ladder-data-2026-11-08.md` |
| 2 | 16 match-list pages (593 finished ladder matches, ids 98830 to 99422), 165 small match pages, the leaderboard, and 36 replays. 35 raw replay files were kept. | `data/ladder-data-2-2026-11-08.md` |
| 3 | The newest 100 finished ladder games of the Scourge cell (matches 103128 to 103747), one match page for each, and 15 replays of games Scourge lost. | `data/scourge-losses-2026-11-08.md` |
| 4 | All 95 finished ladder games of the Contagion cell (matches 103614 to 104195), and 12 replays (6 wins, 6 losses). | `data/contagion-games-2026-11-08.md` |
| 5 | 12 match-list pages (480 finished ladder matches, ids 105881 to 106358), the leaderboard, and 72 match pages and replays: Contagion 18, Complacency 18, and 38 games of the top rivals without our cells. All 72 are in the validation set. | `data/pull5-games-2026-11-08.md` |

Pull 1 and pull 2 were read through a logged-in browser session. Pull 3 and pull 4 used the site's match list and match pages. Pull 5 used the match list, the match pages and the leaderboard, in a logged-in browser session. The offline study of the 35 pull 2 replays is in `data/replay-mining-2026-11-08.md`. Site mechanics and calibration results are in `data/site-observations-2026-11-08.md`. Ratings logged over time are in `data/site-checks.md`.

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
    site/viewer.js                  copy of the site's replay decoder (local only, not in the repository)
    replays/<id>.chr2.gz            raw replays (35 kept; git-ignored, not in the repository)
    keyframes/<id>.kf.json.gz       keyframes for each replay (git-ignored, not in the repository)
    summaries/<id>.json             one summary per replay
    mining/                         output of mine.py and mine_report.py
  pull3/, pull4/ and pull5/
    matches-*.json, names.json      match lists and name tables
    replays/                        raw replays; git-ignored (too large for the repo)
    mining/<id>.json                per-game timelines
    mining/races/<id>.csv.gz        one row per death (refill race)
    validation-table.md, starts.json  tables read by sim/validate.py (tools/valtab.py)
  pull5/
    matchlist-105881-106358.json    the 480 matches of the match list (id, cells, winner)
    matches-pull5-2026-11-08.json   the 72 chosen games with their match pages
    leaderboard-2026-11-08.json     leaderboard snapshot (versions)
  splits/
    split.json                      the FIT or TEST set of every validation match (sim/validate.py)
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
| `tools/pull3/tab.py` | Builds the table of Scourge games. It also writes `data/pull3/names.json`. Games without `--cell` are left out of the tables but kept in `names.json`, so one list can hold the games of several cells (pull 5). |
| `tools/pull3/losses.py` | Builds a timeline for each game Scourge lost. |
| `tools/pull4/tab.py` | Builds the table of Contagion games, with a Contagion against Scourge comparison. |
| `tools/pull4/games.py` | Builds a timeline for each Contagion game. |
| `tools/privacy_check.py` | Looks for local paths, personal text and model names in the files. |

## Doing your own pull

The repository does not contain the replays. They are too large (25 to 53 MB each, gzipped). To use the replay tools, collect your own pull. The tools that need replays stop with the message "run a pull first" when the files are missing.

**What you need.** The site is https://cellhack2.hostbin.org/. You must log in with a class account to read the match pages and the replays. You also need Python 3.12. The decoder uses only the standard library.

Follow the [pacing rules](#pacing-rules-for-the-site) in the next section during every step that reads the site.

### Step 1: choose a pull name

Use the next free name, for example `pull5`. All files of the pull go into `data/pull5/`. The steps below use `<pull>` for this name.

### Step 2: save the match list as JSON

Open the site's match list for the cell you study, and open the match page of each game. Write the data into one JSON file, for example `data/<pull>/matches-<cell>-<date>.json`. The tab scripts read this schema:

```json
{
  "utc": "2026-11-08T14:49:23.507Z",
  "source": "where the list came from (free text)",
  "note": "what the list holds (free text)",
  "matches": [
    {
      "id": 103747,
      "cells": ["Noob+", "Brawler", "zergling", "Scourge"],
      "winner": "Scourge",
      "colonies": [
        {"name": "Noob+", "player": "Assembler", "place": "2", "pop": "0", "peak": "1768",
         "energy": "0", "faults": "0", "insns": "22 (37)", "rating": "1202 → 1210"}
      ]
    }
  ]
}
```

- `colonies` has one entry for each of the four colonies. Each value is the text from the match page table.
- Keep `colonies` in the order of the match page table. This order is the colony order of the replay (colony 0 to 3). The project checked this on all 27 replays of pull 3 and pull 4: the places and the final populations agree.
- The tab scripts use `id`, and for each colony `name`, `place`, `pop` and `rating`. `place` is the text `"1"` to `"4"`. `rating` holds two numbers: the rating before and after the match.
- A name can start with an emoji, as on the site. The tools remove it.
- `lists.py` reads only `id`, `cells` and `winner`. It reads only pull 2.

### Step 3: build names.json

Run the tab script on your list. It prints the tables and writes `data/<pull>/names.json`, which maps each match id to the four colony names in colony order.

```
python -I tools/pull3/tab.py --pull <pull> --cell <your cell> --matches data/<pull>/matches-<cell>-<date>.json
```

`tools/pull4/tab.py` takes the same arguments and also `--rival <cell>`, to compare two of your cells in the same games. Every replay you download must have its match id in this list. Else `mine.py` and `valtab.py` cannot name its colonies.

### Step 4: download the replays

The site serves the replay of match `<id>` at `/api/matches/<id>/replay`, for a logged-in session. Save each replay as `data/<pull>/replays/<id>.chr2.gz`. The tools read this file with gzip.

Pull 5 did this from a page of the site. `fetch()` returns the bytes already decompressed. The page compressed them again with `CompressionStream('gzip')` and saved them through a download link. Then the files were moved from the download folder into the replays folder.

- The file must be gzip-compressed. A replay that the browser has already decompressed starts with the bytes `CHR2` (about 100 MB for 3000 ticks). Compress it with this command:

  ```
  python -c "import gzip,shutil,sys; f=sys.argv[1]; g=gzip.open(f+'.gz','wb'); shutil.copyfileobj(open(f,'rb'),g); g.close()" 103747.chr2
  ```

  Then move `103747.chr2.gz` into `data/<pull>/replays/`.
- A file that already starts with the bytes `1f 8b` is gzip-compressed. Keep it as it is.
- Only format version 4 is decoded. The tools stop with an error for other versions.
- Wait between downloads (see the pacing rules). Do not download in parallel.
- Do not commit the replays. `.gitignore` ignores `data/pull*/replays/`.

### Step 5: decode the replays

```
CH_PULL=<pull> python -I tools/pull2/mine.py
```

On Windows PowerShell, set the variable first: `$env:CH_PULL = "<pull>"`, then run `python -I tools/pull2/mine.py`. The decoder reads every replay that has no output yet. It writes `data/<pull>/mining/<id>.json` and `data/<pull>/mining/races/<id>.csv.gz`. For each replay it prints the keyframe check. `kfMismatch` and `countMismatch` must be 0. If not, the replay format changed, and the outputs are not reliable.

### Step 6: build the validation table

```
CH_PULL=<pull> python -I tools/valtab.py
```

This writes `data/<pull>/validation-table.md` and `data/<pull>/starts.json` for all replays of the pull. `sim/validate.py` reads only the pulls named in its `PULLS` list, so a new pull must be added there before the simulator uses it.

Then give the new matches a FIT or TEST set. Run `python validate.py --extend-split` in `sim/`. It splits only the matches that have no set yet, and it writes them into `data/splits/split.json`. A match never changes its set after that, because the simulator is tuned on FIT. `validate.py` stops with an error when a match has no set.

### Step 7: tables for each game

`tools/pull3/losses.py` and `tools/pull4/games.py` read the `mine.py` output. Both take `--pull <pull>` and `--cell <your cell>`. `games.py` also takes `--rival <cell>`.

```
python -I tools/pull3/losses.py --pull <pull> --cell <your cell>
python -I tools/pull4/games.py --pull <pull> --cell <your cell> --rival <other cell>
```

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
