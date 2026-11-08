#!/bin/bash
# Move finished browser downloads into data/<pull>/ (replays, keyframes, summaries).
# "name (1).ext" duplicates replace the older file.
# Usage: collect.sh <pull> [DOWNLOADS_DIR]   (default: $DOWNLOADS_DIR, else $HOME/Downloads)
[ -n "$1" ] || { echo "usage: collect.sh <pull> [DOWNLOADS_DIR]" >&2; exit 1; }
D="${2:-${DOWNLOADS_DIR:-$HOME/Downloads}}"
P="$(cd "$(dirname "$0")/../.." && pwd)/data/$1"
mkdir -p "$P/replays" "$P/keyframes" "$P/summaries"
shopt -s nullglob
mv_one() { # file destdir
  f="$1"; b="$(basename "$f")"; clean="$(echo "$b" | sed -E 's/ \([0-9]+\)//')"; mv -f "$f" "$2/$clean"; }
for f in $D/[0-9]*.chr2.gz $D/[0-9]*chr2*.gz; do [ -f "$f" ] && mv_one "$f" $P/replays; done
for f in $D/[0-9]*.kf*.json.gz; do [ -f "$f" ] && mv_one "$f" $P/keyframes; done
for f in $D/[0-9]*.json; do [ -f "$f" ] && mv_one "$f" $P/summaries; done
rm -f "$P/replays/"*" ("*")."* "$P/summaries/"*" ("*")."* 2>/dev/null
echo "replays: $(ls $P/replays | wc -l)  kf: $(ls $P/keyframes | wc -l)  summaries: $(ls $P/summaries | wc -l)"
du -sh $P
