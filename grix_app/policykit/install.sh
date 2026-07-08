#!/usr/bin/env bash
# =============================================================================
# Install Grix's PolicyKit integration
# =============================================================================
# Installs grix-helper and its PolicyKit policy so Grix can request
# elevated privileges through pkexec (a graphical authentication
# prompt) instead of relying solely on sudo in a terminal.
#
# This is OPTIONAL. Grix works fine without it - it automatically
# falls back to running privileged commands with sudo if pkexec or
# this policy isn't installed. Installing it just gets you the nicer
# graphical prompt (and a Grix-branded one) instead of sudo's
# terminal-only password prompt.
#
# Usage:
#   sudo bash policykit/install.sh
#   sudo bash policykit/install.sh --uninstall
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

HELPER_SRC="$SCRIPT_DIR/grix-helper"
POLICY_SRC="$SCRIPT_DIR/com.griffinlinux.grix.policy"

HELPER_DEST="/usr/bin/grix-helper"
POLICY_DEST="/usr/share/polkit-1/actions/com.griffinlinux.grix.policy"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}[grix-polkit]${NC} $*"; }
ok()   { echo -e "${GREEN}[grix-polkit]${NC} $*"; }
err()  { echo -e "${RED}[grix-polkit]${NC} $*" >&2; }
die()  { err "$*"; exit 1; }

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "This script must be run with sudo (it installs files into /usr).
  Try: sudo bash $0"
fi

if [[ "${1:-}" == "--uninstall" ]]; then
    log "Removing Grix PolicyKit integration..."
    rm -f "$HELPER_DEST" "$POLICY_DEST"
    ok "Removed $HELPER_DEST and $POLICY_DEST."
    ok "Grix will fall back to sudo for privileged actions."
    exit 0
fi

[[ -f "$HELPER_SRC" ]] || die "Could not find grix-helper at $HELPER_SRC"
[[ -f "$POLICY_SRC" ]] || die "Could not find policy file at $POLICY_SRC"

command -v pkexec >/dev/null 2>&1 || {
    err "pkexec was not found on this system."
    err "PolicyKit (polkit) may not be installed. Install it first, e.g.:"
    err "  sudo apt install policykit-1"
    exit 1
}

log "Installing grix-helper to $HELPER_DEST..."
install -m 0755 -o root -g root "$HELPER_SRC" "$HELPER_DEST"
ok "Installed."

log "Installing PolicyKit policy to $POLICY_DEST..."
install -m 0644 -o root -g root "$POLICY_SRC" "$POLICY_DEST"
ok "Installed."

echo ""
ok "Grix's PolicyKit integration is now installed."
echo "  Privileged repairs will show a graphical authentication prompt"
echo "  via pkexec instead of needing a terminal for sudo."
echo ""
echo "  To remove it later: sudo bash $0 --uninstall"
echo ""
