# Data pulls and replay tools

The site serves each match's replay as a separate file. The project collects match lists, match pages and replays in rounds called **pulls**, then decodes the replays into tables and write-ups.

## The pulls

All five pulls were collected on 2026-11-08 through a logged-in browser session.

| Pull | What it collected | Main write-up |
|---|---|---|
| 1 | 10 match-list pages (398 finished ladder matches, ids 98432 to 98829), 13 replays, a few match pages, and the leaderboard. | `data/ladder-data-2026-11-08.md` |
| 2 | 16 match-list pages (593 finished ladder matches, ids 98830 to 99422), 165 small match pages, the leaderboard, and 36 replays. 35 raw replay files were kept. | `data/ladder-data-2-2026-11-08.md` |
| 3 | The newest 100 finished ladder games of the Scourge cell (matches 103128 to 103747), one match page for each, and 15 replays of games Scourge lost. | `data/scourge-losses-2026-11-08.md` |
| 4 | All 95 finished ladder games of the Contagion cell (matches 103614 to 104195), and 12 replays (6 wins, 6 losses). | `data/contagion-games-2026-11-08.md` |
| 5 | 12 match-list pages (480 finished ladder matches, ids 105881 to 106358), the leaderboard, and 72 match pages and replays: Contagion 18, Complacency 18 (2 games hold both cells), and 38 games of the top rivals without our cells. | `data/pull5-games-2026-11-08.md` |

Pulls 2 to 5 supply the 135 matches of the simulator's validation pool (36 + 15 + 12 + 72); pull 1's 13 replays are not in the pool. FIT and TEST sizes are in [simulator.md](simulator.md). Site mechanics and calibration results are in `data/site-observations-2026-11-08.md`. Ratings over time are in `data/site-checks.md`.

## What the site gives

| Item | What it contains |
|---|---|
| Leaderboard | For each cell: rating, games, wins, average place and average instructions per call. |
| Match list | The finished matches for a cell or for the whole ladder. |
| Match page | For each colony: player, place, final population, peak population, energy, faults, instructions per call (average and maximum), and the rating before and after the match. |
| Replay | The full record of one match, as a gzip-compressed binary file of the form `CHR2`. Pull 5's replays are 2 to 62 MB each. |

## How a replay is read

A replay is a binary stream. The site's page decodes it with `CellHackViewer.decode`. The decoded data has these parts:

- **Header.** Format version 4, ruleset 9, a 64 by 64 board, 3000 ticks, the seed, the colony ids, and a keyframe every 50 ticks.
- **Keyframes.** A full list of the living cells every 50 ticks: id, colony, position and energy.
- **Ticks.** For each tick, the population of each colony, the energy of every cell, and the list of events.
- **Events.** Five kinds: a birth (k1), a move (k2), a death (k3), an eat (k4) and a feed (k5).
- **End.** The final placement, the populations, the reason the match ended, and the number of ticks run.

Events within a tick are in turn order, so the studies can measure which colony acted first.

## The decoder

`tools/replay/mine.py` is a pure Python version of the site's decoder. It streams one replay at a time, compares the state at the start of each tick with the keyframes, and checks that the count of energy values matches the count of living cells. All 35 pull 2 replays matched all 1732 keyframes, and pulls 3 and 4 reported 0 mismatches. It runs in about 2 to 8 seconds per replay, on one process at below-normal priority.

`mine.py` runs two analyses:

- **Refill race.** For every death: which colony took the freed square, how many ticks later, the energy of the new cell, and which colonies were next to the square.
- **Resting income.** For every cell and tick with no event: the energy change, by starting energy.

## Layout of the data folder


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
    validation-table.md, starts.json  tables read by sim/validate.py
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
    validation-table.md, starts.json  tables read by sim/validate.py (tools/replay/valtab.py)
  pull5/
    matchlist-105881-106358.json    the 480 matches of the match list (id, cells, winner)
    matches-pull5-2026-11-08.json   the 72 chosen games with their match pages
    leaderboard-2026-11-08.json     leaderboard snapshot (versions)
  splits/
    split.json                      the FIT or TEST set of every validation match (sim/validate.py)
```

## Tools

Run each tool from the repository root. The replay tools are in `tools/replay/`. Each one works on one pull, named with `--pull <pull>`. There is no default pull. Without `--pull`, a tool stops and names the folders it found in `data/`.

| Tool | What it does |
|---|---|
| `tools/replay/tab.py` | Builds the table of one cell's games from a saved match list, and writes `data/<pull>/names.json`. Run `python -I tools/replay/tab.py --pull <pull> --cell <cell>`. Options: `--matches FILE` (default: the one `data/<pull>/matches-*.json`), `--rival <cell>` (a same-game comparison with a second cell), `--parts 2` or `3` (rating trend in halves or thirds). Games without `--cell` are left out of the tables but kept in `names.json`, so one list can hold the games of several cells. |
| `tools/replay/mine.py` | The decoder and the two analyses. Run `python -I tools/replay/mine.py --pull <pull> [replay ids]`. |
| `tools/replay/valtab.py` | Builds `validation-table.md` and `starts.json` of a pull for the simulator. Run `python -I tools/replay/valtab.py --pull <pull>`. |
| `tools/replay/losses.py` | Builds a timeline for each game that a cell lost. Run with `--pull <pull> --cell <cell>`. |
| `tools/replay/games.py` | Builds a timeline for each game of a cell, with the key rival of each game. Run with `--pull <pull> --cell <cell>`, and optionally `--rival <cell>`. |
| `tools/replay/mine_report.py` | Combines the mining output of a pull by cell name into tables. Run with `--pull <pull>`. `--cell <cell> --rivals <a>,<b>` adds the refill races between that cell and those rivals. |
| `tools/replay/actions.py` | Shows, for one replay, what each cell did when an enemy was next to it. Run with `--pull <pull> <replay id>`. |
| `tools/replay/birth_order.py` | Ranks the split order of the colonies in the same tick. Run with `--pull <pull> <tmin> <replay ids>`. |
| `tools/replay/collect.sh` | Moves finished files saved by the browser into `data/<pull>/`. Run `tools/replay/collect.sh <pull> [downloads folder]`. It removes the number the browser adds to a repeated file name, so the newer copy replaces the older one. |
| `tools/privacy_check.py` | Looks for local paths, personal text and model names in the files. |


**History tools.** These scripts reproduce the pull 2 report and read only `data/pull2`.

| Tool | What it does |
|---|---|
| `tools/pull2/analyze.js` | The browser-side analyzer used in pull 2. It ran inside the replay page. |
| `tools/pull2/report.py` | Builds summary tables from the summaries. |
| `tools/pull2/lists.py` | Win rates and head-to-heads from the pull 2 match list. |
| `tools/pull2/select_sprint.py` | Lists matches with Sprint, and how Sprint fared in each. |
| `tools/pull2/late.py` | Finds the largest population changes after tick 500, and the freeze tick of each match. |
| `tools/pull2/sec8.py` | Builds the table of matches chosen for study and why. |

**Old paths.** The dated write-ups use older paths, such as `tools/pull2/mine.py`, `tools/pull3/tab.py`, `tools/pull4/games.py` and `tools/valtab.py`. These files still exist. Each runs its `tools/replay/` tool with the defaults it had then, and they accept `CH_PULL`. Use `tools/replay/` for new work.

## Doing your own pull

The repository does not contain the replays. To use the replay tools, collect your own pull. Tools that need replays stop with "run a pull first" when the files are missing.

**What you need.** The site is https://cellhack2.hostbin.org/. A class account login is needed for match pages and replays. Python 3.12. The decoder uses only the standard library.

Follow the [pacing rules](#pacing-rules-for-the-site) during every step that reads the site.

### Step 1: choose a pull name

Choose a new folder name, for example `mypull`. All files go into `data/<pull>/`. The tools find the pull from its folder.

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

- `colonies` has one entry per colony, in the order of the match page table. This order is the replay's colony order (checked on all 27 replays of pulls 3 and 4). Values are the text from the page.
- The tab scripts use `id`, and per colony `name`, `place` (`"1"` to `"4"`), `pop` and `rating` (before and after).
- A name can start with an emoji. The tools remove it.

### Step 3: build names.json

This prints the tables and writes `data/<pull>/names.json`, which maps each match id to the four colony names in colony order.

```
python -I tools/replay/tab.py --pull <pull> --cell <your cell>
```

With exactly one `matches-*.json`, the script reads it. Otherwise use `--matches FILE`. Every replay must have its match id in this list, or `mine.py` and `valtab.py` cannot name its colonies.

### Step 4: download the replays

The site serves the replay of match `<id>` at `/api/matches/<id>/replay`, for a logged-in session. Save each replay as `data/<pull>/replays/<id>.chr2.gz`. The tools read this file with gzip.

From a logged-in page, `fetch()` returns the bytes already decompressed. Compress them again with `CompressionStream('gzip')` and save them through a download link. `tools/replay/collect.sh <pull>` moves the files into place.

- The file must be gzip-compressed. A file that the browser already decompressed starts with the bytes `CHR2`. Compress it with:

  ```
  python -c "import gzip,shutil,sys; f=sys.argv[1]; g=gzip.open(f+'.gz','wb'); shutil.copyfileobj(open(f,'rb'),g); g.close()" 103747.chr2
  ```

  Then move `103747.chr2.gz` into `data/<pull>/replays/`.
- A file that starts with the bytes `1f 8b` is already gzip-compressed.
- Only format version 4 is decoded. The tools stop with an error for other versions.
- Download one replay at a time, at least 30 seconds apart.
- Do not commit the replays. `.gitignore` ignores `data/*/replays/` and `data/*/keyframes/`.

### Step 5: decode the replays

```
python -I tools/replay/mine.py --pull <pull>
```

The decoder reads every replay with no output yet and writes `data/<pull>/mining/<id>.json` and `mining/races/<id>.csv.gz`. `kfMismatch` and `countMismatch` must be 0. If not, the format changed and the outputs are not reliable.

### Step 6: build the validation table

```
python -I tools/replay/valtab.py --pull <pull>
```

This writes `validation-table.md` and `starts.json` in `data/<pull>/`. `sim/validate.py` uses every folder of `data/` that has a `validation-table.md`. To replay only your pull, run `python validate.py --pull <pull>` in `sim/`.

Then run `python validate.py --extend-split` in `sim/`. It gives a set only to matches that have none, and writes `data/splits/split.json`. `--split <file>` uses another file, for every later run. A match never changes set. `validate.py` stops with an error when a match has no set.

A cell with no sim model is played by the hunter bot, with a warning. Use `--models '{"<cell>": "<sim spec>"}'` or `--models <file.json>` to give it one.

### Step 7: tables for each game

`losses.py` and `games.py` read the `mine.py` output. Games without `--cell` are left out, and the count is printed.

```
python -I tools/replay/losses.py --pull <pull> --cell <your cell>
python -I tools/replay/games.py --pull <pull> --cell <your cell> --rival <other cell>
```

## Pacing rules for the site

These rules apply to every request to the site.

1. **One request at a time.** Do not send requests in parallel.
2. **Pages at least 15 seconds apart.** This applies to every site interaction: pages, match lists, the leaderboard, match pages and Sandbox runs.
3. **Replays and other large downloads at least 30 seconds apart.**
4. **Cell creation at least 30 seconds apart.**
5. **On HTTP 429 or an error, wait.** Wait at least 60 seconds before the next request. If the error comes again, double the wait each time, up to 5 minutes.
6. **Check the small pages first.** Read the leaderboard before you fetch large files. It shows whether the rival cells changed version.
7. **Use stored data first.** Fetch only what the stored data does not already give.


## Pitfalls for new readers

- **Rests are not logged.** Resting income is measured from cells with no event.
- **Splits show only the child.** A splitting parent appears as an event-free cell with a negative energy change.
- **Energy is read at the end of a tick.**
- **Facts from one pull may not hold for another.** Each write-up states the match ids it covers.

## Related documents

- `data/ladder-data-2-2026-11-08.md`: the main study of pull 2, with its headline findings and rival profiles.
- `data/replay-mining-2026-11-08.md`: the refill race and resting income, from the 35 pull 2 replays.
- [cells-and-experiments.md](cells-and-experiments.md): how these findings became cell designs.
