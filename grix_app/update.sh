#!/usr/bin/env bash
# =============================================================================
# Grix Update Script
# =============================================================================
# Pulls the latest version from the GitHub repository and reinstalls Grix.
# Preserves your data (~/.local/share/grix/) - scan history, progress, and
# settings are never touched by this script.
#
# Usage:
#   bash update.sh               (from inside the grix_app directory)
#   bash update.sh --check       (only check for updates, don't install)
#   bash update.sh --force       (skip version check and reinstall anyway)
# =============================================================================

set -euo pipefail

REPO_URL="https://github.com/griffin-linux/grix"   # update with your actual repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$HOME/.local/share/grix"
VENV_DIR="$SCRIPT_DIR/.venv"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${CYAN}[Grix]${NC} $*"; }
ok()   { echo -e "${GREEN}[Grix]${NC} $*"; }
warn() { echo -e "${YELLOW}[Grix]${NC} $*"; }
err()  { echo -e "${RED}[Grix]${NC} $*" >&2; }
die()  { err "$*"; exit 1; }

CHECK_ONLY=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --check) CHECK_ONLY=true ;;
        --force) FORCE=true ;;
        --help|-h)
            echo "Usage: $0 [--check] [--force]"
            echo "  --check   Only check if an update is available"
            echo "  --force   Reinstall even if already on the latest version"
            exit 0
            ;;
        *) warn "Unknown argument: $arg (ignored)" ;;
    esac
done

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}          Grix Update Script${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------

log "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || die "python3 is not installed."
command -v pip3 >/dev/null 2>&1 || die "pip3 is not installed."
command -v git >/dev/null 2>&1 || die "git is not installed (needed to check for updates)."

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_MAJOR=3
REQUIRED_MINOR=10

MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [[ "$MAJOR" -lt "$REQUIRED_MAJOR" || ( "$MAJOR" -eq "$REQUIRED_MAJOR" && "$MINOR" -lt "$REQUIRED_MINOR" ) ]]; then
    die "Grix requires Python 3.10 or later. You have Python $PYTHON_VERSION."
fi
ok "Python $PYTHON_VERSION found."

# ---------------------------------------------------------------------------
# Check for updates
# ---------------------------------------------------------------------------

log "Checking for updates..."

CURRENT_COMMIT=""
if [[ -d "$SCRIPT_DIR/.git" ]]; then
    CURRENT_COMMIT=$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
fi

REMOTE_COMMIT=""
if git ls-remote --exit-code "$REPO_URL" HEAD >/dev/null 2>&1; then
    REMOTE_COMMIT=$(git ls-remote "$REPO_URL" HEAD | awk '{print $1}')
fi

if [[ -n "$CURRENT_COMMIT" && -n "$REMOTE_COMMIT" && "$CURRENT_COMMIT" == "$REMOTE_COMMIT" && "$FORCE" == false ]]; then
    ok "Already up to date (commit $CURRENT_COMMIT)."
    if [[ "$CHECK_ONLY" == true ]]; then
        exit 0
    fi
    warn "Use --force to reinstall anyway."
    exit 0
fi

if [[ "$CHECK_ONLY" == true ]]; then
    if [[ -n "$REMOTE_COMMIT" && "$CURRENT_COMMIT" != "$REMOTE_COMMIT" ]]; then
        log "Update available: $CURRENT_COMMIT → $REMOTE_COMMIT"
        echo ""
        echo "Run without --check to install it."
    else
        warn "Could not determine remote version (network issue or not a git clone)."
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# Protect user data
# ---------------------------------------------------------------------------

log "User data directory: $DATA_DIR"
if [[ -d "$DATA_DIR" ]]; then
    ok "Your scan history, progress, and settings are stored in $DATA_DIR and will NOT be touched."
else
    log "No existing data directory found - nothing to preserve."
fi

# ---------------------------------------------------------------------------
# Pull latest source
# ---------------------------------------------------------------------------

if [[ -d "$SCRIPT_DIR/.git" ]]; then
    log "Pulling latest changes from git..."
    git -C "$SCRIPT_DIR" pull --ff-only || {
        warn "git pull failed (merge conflicts or network issue). Trying a hard reset..."
        git -C "$SCRIPT_DIR" fetch origin
        git -C "$SCRIPT_DIR" reset --hard origin/main
    }
    NEW_COMMIT=$(git -C "$SCRIPT_DIR" rev-parse HEAD)
    ok "Updated to commit $NEW_COMMIT."
else
    warn "Not a git repository - can't pull automatically."
    warn "Please download the latest version from: $REPO_URL"
    warn "Then re-run this script from the new directory."
    exit 1
fi

# ---------------------------------------------------------------------------
# Install / update Python dependencies
# ---------------------------------------------------------------------------

log "Updating dependencies..."

if [[ -d "$VENV_DIR" ]]; then
    log "Using existing virtual environment at $VENV_DIR"
    PYTHON="$VENV_DIR/bin/python"
    PIP="$VENV_DIR/bin/pip"
else
    log "No virtual environment found. Installing into user site-packages."
    PYTHON="python3"
    PIP="pip3"
fi

"$PIP" install --upgrade pip --quiet
"$PIP" install --upgrade -r "$SCRIPT_DIR/requirements.txt" --quiet
ok "Dependencies updated."

# ---------------------------------------------------------------------------
# Reinstall the package
# ---------------------------------------------------------------------------

log "Reinstalling Grix..."
"$PIP" install --upgrade -e "$SCRIPT_DIR" --quiet
ok "Grix reinstalled."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  Grix updated successfully!${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Run Grix:    python3 -m grix.main"
echo "  Or, if installed:  grix"
echo ""
