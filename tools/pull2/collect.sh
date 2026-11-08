#!/bin/bash
# Old path of tools/replay/collect.sh, kept so that the dated reports in data/ still apply: it collects into data/pull2/.
# For your own pull use:  tools/replay/collect.sh <pull> [DOWNLOADS_DIR]
exec "$(dirname "$0")/../replay/collect.sh" pull2 "$@"
