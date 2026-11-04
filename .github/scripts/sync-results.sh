#!/usr/bin/env bash
# Polls the SF Department of Elections summary.xml and publishes validated changes.
#
#   sync-results.sh poll <iterations>   Check every 30s; on change, commit data/summary.xml
#                                       straight to gh-pages (no rebuild needed).
#   sync-results.sh prepare-build       Write the best available XML into public/data for a
#                                       full Vite build (upstream if valid, else what is live).
#
# The live copy is read from the gh-pages branch rather than the Pages CDN, because Fastly
# ignores query strings and can serve a copy up to 10 minutes old.
set -uo pipefail

UPSTREAM_URL="${UPSTREAM_URL:-https://sfelections.org/results/20261103/data/summary.xml}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
DATA_PATH="data/summary.xml"
PUBLIC_XML="src/frontend/dashboard/public/data/summary.xml"
MIN_CONTESTS="${MIN_CONTESTS:-50}"
POLL_INTERVAL="${POLL_INTERVAL:-30}"
WORK="$(mktemp -d)"
WORKTREE="$WORK/gh-pages"
trap 'git worktree remove --force "$WORKTREE" >/dev/null 2>&1; rm -rf "$WORK"' EXIT

log() { echo "[$(date -u +'%H:%M:%S UTC')] $*"; }

# Prints "<ballots3> <report title>" for a complete SSRS summary report, or fails.
inspect_xml() {
  python3 - "$1" "$MIN_CONTESTS" <<'PY'
import sys
import xml.etree.ElementTree as ET

path, min_contests = sys.argv[1], int(sys.argv[2])
try:
    root = ET.parse(path).getroot()
except Exception as exc:
    sys.exit(f"not well-formed XML: {exc}")
contests = root.findall(".//{*}ContestIdGroup")
if len(contests) < min_contests:
    sys.exit(f"only {len(contests)} contests (expected >= {min_contests})")
elector = root.find(".//{*}electorGroupId2")
if elector is None:
    sys.exit("missing RegistrationAndTurnout electorGroupId2")
ballots = int((elector.get("ballots3") or "0").replace(",", "") or 0)
title = root.find(".//{*}Title/{*}Report")
lines = (title.get("Textbox8", "") if title is not None else "").replace("\r", "").split("\n")
print(ballots, lines[-1].strip() if lines else "")
PY
}

fetch_upstream() {
  curl -fsSL -m 20 --retry 2 --retry-delay 3 -A "$UA" "${UPSTREAM_URL}?_cb=$(date +%s)" -o "$1"
}

fetch_live() {
  git fetch --quiet --depth=1 origin +refs/heads/gh-pages:refs/remotes/origin/gh-pages &&
    git show "origin/gh-pages:${DATA_PATH}" > "$1"
}

# Commits $1 to gh-pages unless gh-pages already has it or it would roll ballots backwards.
publish() {
  local src="$1" label="$2" attempt
  local new_ballots
  new_ballots="$(inspect_xml "$src" | cut -d' ' -f1)"
  for attempt in 1 2 3; do
    git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
    if ! git fetch --quiet --depth=1 origin +refs/heads/gh-pages:refs/remotes/origin/gh-pages ||
       ! git worktree add --quiet --detach "$WORKTREE" origin/gh-pages; then
      log "Could not check out gh-pages (attempt $attempt)."
      sleep 5
      continue
    fi

    if cmp -s "$src" "$WORKTREE/$DATA_PATH"; then
      log "gh-pages already has this XML."
      return 0
    fi
    local live_ballots
    live_ballots="$(inspect_xml "$WORKTREE/$DATA_PATH" 2>/dev/null | cut -d' ' -f1)"
    if [ -n "$live_ballots" ] && [ "$new_ballots" -lt "$live_ballots" ]; then
      echo "::warning::Upstream ballots ($new_ballots) are below live ballots ($live_ballots); not publishing. Run workflow_dispatch with force=true if SF really revised totals down."
      [ "${FORCE:-false}" = "true" ] || return 0
    fi

    cp "$src" "$WORKTREE/$DATA_PATH"
    git -C "$WORKTREE" add "$DATA_PATH"
    git -C "$WORKTREE" -c user.name="github-actions[bot]" \
      -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
      commit --quiet -m "Update summary.xml: ${label}"
    if git -C "$WORKTREE" push --quiet origin HEAD:refs/heads/gh-pages; then
      log ">>> Published ${label} to gh-pages."
      return 0
    fi
    log "Push to gh-pages rejected (attempt $attempt); retrying on latest gh-pages."
    sleep 3
  done
  echo "::error::Failed to publish ${label} to gh-pages after 3 attempts."
  return 1
}

cmd_poll() {
  local iterations="$1" i info
  fetch_live "$WORK/live.xml" || : > "$WORK/live.xml"
  log "Polling ${UPSTREAM_URL} ${iterations}x at ${POLL_INTERVAL}s intervals."
  for i in $(seq 1 "$iterations"); do
    if ! fetch_upstream "$WORK/latest.xml"; then
      log "Check $i/$iterations: upstream fetch failed."
    elif ! info="$(inspect_xml "$WORK/latest.xml" 2>&1)"; then
      echo "::warning::Check $i/$iterations: rejected upstream XML (${info})."
    elif cmp -s "$WORK/latest.xml" "$WORK/live.xml"; then
      log "Check $i/$iterations: unchanged (${info#* }, ballots ${info%% *})."
    else
      log "Check $i/$iterations: NEW XML (${info#* }, ballots ${info%% *})."
      if publish "$WORK/latest.xml" "${info#* } (${info%% *} ballots)"; then
        cp "$WORK/latest.xml" "$WORK/live.xml"
      fi
    fi
    [ "$i" -lt "$iterations" ] && sleep "$POLL_INTERVAL"
  done
  return 0
}

cmd_prepare_build() {
  local info
  mkdir -p "$(dirname "$PUBLIC_XML")"
  if fetch_upstream "$WORK/latest.xml" && info="$(inspect_xml "$WORK/latest.xml" 2>&1)"; then
    local live_ballots=""
    if fetch_live "$WORK/live.xml"; then
      live_ballots="$(inspect_xml "$WORK/live.xml" 2>/dev/null | cut -d' ' -f1)"
    fi
    if [ -z "$live_ballots" ] || [ "${info%% *}" -ge "$live_ballots" ] || [ "${FORCE:-false}" = "true" ]; then
      cp "$WORK/latest.xml" "$PUBLIC_XML"
      log "Building with upstream XML (${info#* }, ballots ${info%% *})."
      return 0
    fi
    echo "::warning::Upstream ballots (${info%% *}) below live (${live_ballots}); building with live XML."
  else
    echo "::warning::Upstream XML unavailable or invalid (${info:-fetch failed}); building with live XML."
  fi
  if [ -s "$WORK/live.xml" ] || fetch_live "$WORK/live.xml"; then
    cp "$WORK/live.xml" "$PUBLIC_XML"
  else
    echo "::warning::Could not read live XML from gh-pages; building with checked-in summary.xml."
  fi
}

case "${1:-}" in
  poll) cmd_poll "${2:-1}" ;;
  prepare-build) cmd_prepare_build ;;
  inspect) inspect_xml "$2" ;;
  *) echo "usage: $0 poll <iterations> | prepare-build | inspect <file>" >&2; exit 2 ;;
esac
