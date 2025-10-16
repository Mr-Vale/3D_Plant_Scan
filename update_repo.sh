#!/usr/bin/env bash
# Update a local directory from a GitHub repo WITHOUT deleting extra local files.
# - Overwrites existing files with latest from the repo
# - Adds any new files from the repo
# - Leaves any extra local files alone (no deletions)
#
# Usage:
#   bash update_repo.sh --repo https://github.com/Mr-Vale/RootBox-Software.git [--branch main] [--workdir ~/RootBox] [--cache-dir <path>]
#
# Examples:
#   bash update_repo.sh --repo https://github.com/Mr-Vale/RootBox-Software.git --workdir ~/RootBox
#   bash update_repo.sh --repo https://github.com/Mr-Vale/Network_Logger.git --workdir ~/Network_Logger
#   bash update_repo.sh --repo https://github.com/Mr-Vale/3D_Plant_Scan.git --workdir ~/3D_Plant_Scan
#
# Requirements: git, rsync

set -euo pipefail

usage() {
  cat <<EOF
Usage: bash $0 --repo <url> [--branch <name>] [--workdir <path>] [--cache-dir <path>]

Options:
  --repo       Git repository URL (required), e.g. https://github.com/owner/repo.git
  --branch     Branch to pull (optional). If omitted, script tries to detect the repo's default branch; falls back to 'main'
  --workdir    Target directory to update (optional). Defaults to current directory
  --cache-dir  Directory to keep a shallow clone for fast updates (optional). Defaults to <workdir>/.repo_cache_<repo>

This script overlays files from the repo onto --workdir WITHOUT deleting extra local files.
EOF
}

# Parse args
REPO_URL=""
BRANCH=""
WORKDIR="$(pwd)"
CACHE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="${2:-}"; shift 2;;
    --branch) BRANCH="${2:-}"; shift 2;;
    --workdir) WORKDIR="${2:-}"; shift 2;;
    --cache-dir) CACHE_DIR="${2:-}"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1;;
  esac
done

if [[ -z "$REPO_URL" ]]; then
  echo "Error: --repo is required" >&2
  usage
  exit 1
fi

# Ensure tools exist
command -v git >/dev/null 2>&1 || { echo "Error: git not found"; exit 1; }
command -v rsync >/dev/null 2>&1 || { echo "Error: rsync not found"; exit 1; }

log() { printf "%s %s\n" "$(date '+[%Y-%m-%d %H:%M:%S]')" "$*"; }

# Determine default branch if not provided
if [[ -z "$BRANCH" ]]; then
  # Try to discover the repo's default branch remotely
  DEFAULT_BRANCH="$(git ls-remote --symref "$REPO_URL" HEAD 2>/dev/null | awk '/^ref:/ {print $2}' | sed 's|refs/heads/||')"
  BRANCH="${DEFAULT_BRANCH:-main}"
fi

# Derive cache dir if not provided
if [[ -z "$CACHE_DIR" ]]; then
  # Strip trailing .git if present
  REPO_BASENAME="$(basename "${REPO_URL%%.git}")"
  CACHE_DIR="${WORKDIR}/.repo_cache_${REPO_BASENAME}"
fi

log "Repo URL: $REPO_URL"
log "Branch:   $BRANCH"
log "Workdir:  $WORKDIR"
log "Cache:    $CACHE_DIR"

mkdir -p "$WORKDIR"

# Prepare or update cache clone (shallow)
if [[ -d "$CACHE_DIR/.git" ]]; then
  log "Updating cache clone..."
  git -C "$CACHE_DIR" remote set-url origin "$REPO_URL" || true
  git -C "$CACHE_DIR" fetch --depth=1 origin "$BRANCH"
  git -C "$CACHE_DIR" checkout -f "$BRANCH"
  git -C "$CACHE_DIR" reset --hard "origin/$BRANCH"
else
  log "Creating cache clone..."
  mkdir -p "$CACHE_DIR"
  git clone --depth=1 --branch "$BRANCH" "$REPO_URL" "$CACHE_DIR"
fi

REV="$(git -C "$CACHE_DIR" rev-parse --short HEAD || echo unknown)"
log "Repo at commit: $REV"

# Sync from cache into workdir WITHOUT deleting extra local files
log "Syncing files into $WORKDIR (no deletions)..."
rsync -a \
  --exclude ".git" \
  "$CACHE_DIR"/ \
  "$WORKDIR"/

log "Update complete."