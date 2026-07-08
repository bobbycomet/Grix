#!/usr/bin/env bash
# =============================================================================
# Grix AppImage Builder
# =============================================================================
# Builds a portable, single-file AppImage for Grix using appimagetool.
#
# Prerequisites:
#   - appimagetool   (download from https://github.com/AppImage/appimagetool)
#   - python3        (3.10 or newer)
#   - pip3
#
# Usage:
#   bash build_appimage.sh
#   bash build_appimage.sh --output /path/to/Grix-x86_64.AppImage
#   bash build_appimage.sh --arch arm64      (for cross-arch, needs QEMU)
#
# What it does:
#   1. Creates an AppDir layout at /tmp/GrixAppDir/
#   2. Installs Grix + dependencies into a self-contained Python prefix
#      inside the AppDir (no system packages are touched)
#   3. Bundles grix-helper and its PolicyKit policy inside the AppImage,
#      and has AppRun offer a one-time, explicit-consent install of them
#      to the real system locations on first run (needed since pkexec
#      cannot read policy files from inside a squashfs image - see
#      "PolicyKit and AppImages" below)
#   4. Embeds the AppRun launcher script and .desktop/.png files
#   5. Calls appimagetool to package everything into a single .AppImage
#
# PolicyKit and AppImages:
#   pkexec only trusts policy (.policy) files installed at
#   /usr/share/polkit-1/actions/ on the real filesystem - it has no
#   concept of "look inside this AppImage". So Grix's PolicyKit
#   integration can't be made to work purely from inside the bundle;
#   the helper script and policy file have to actually land on the
#   user's system. This script bundles both inside the AppImage
#   payload, and AppRun prompts (once, via a single pkexec
#   authentication) to install them on first launch - or a user can
#   skip this and Grix falls back to plain pkexec/sudo for privileged
#   actions, same as running from source.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPDIR="/tmp/GrixAppDir"
OUTPUT_DIR="$SCRIPT_DIR/dist"
OUTPUT_NAME="Grix-x86_64.AppImage"
ARCH="x86_64"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${CYAN}[build]${NC} $*"; }
ok()   { echo -e "${GREEN}[build]${NC} $*"; }
warn() { echo -e "${YELLOW}[build]${NC} $*"; }
err()  { echo -e "${RED}[build]${NC} $*" >&2; }
die()  { err "$*"; exit 1; }

for arg in "$@"; do
    case "$arg" in
        --output=*) OUTPUT_NAME="${arg#*=}" ;;
        --output)   shift; OUTPUT_NAME="$1" ;;
        --arch=*)   ARCH="${arg#*=}" ;;
        --arch)     shift; ARCH="$1" ;;
        --help|-h)
            echo "Usage: $0 [--output <path>] [--arch <x86_64|arm64>]"
            exit 0
            ;;
    esac
done

OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_NAME"

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}          Grix AppImage Builder${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

log "Checking prerequisites..."

command -v python3 >/dev/null 2>&1  || die "python3 is required."
command -v pip3    >/dev/null 2>&1  || die "pip3 is required."

APPIMAGETOOL=""
for candidate in appimagetool appimagetool-"$ARCH".AppImage ./appimagetool ./appimagetool-"$ARCH".AppImage; do
    if command -v "$candidate" >/dev/null 2>&1; then
        APPIMAGETOOL="$candidate"
        break
    fi
done

if [[ -z "$APPIMAGETOOL" ]]; then
    die "appimagetool not found. Download it from:
    https://github.com/AppImage/appimagetool/releases
Then place it in your PATH or in this directory and make it executable:
    chmod +x appimagetool-x86_64.AppImage"
fi

ok "Using appimagetool: $APPIMAGETOOL"
ok "Architecture: $ARCH"
ok "Output: $OUTPUT_PATH"

BUILD_PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Build machine Python: $BUILD_PYTHON_VERSION"

# ---------------------------------------------------------------------------
# Clean previous build
# ---------------------------------------------------------------------------

log "Cleaning previous build..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib/python"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Install Grix and deps into the AppDir prefix
# ---------------------------------------------------------------------------

log "Installing Grix and dependencies into AppDir..."
PYTHON_PREFIX="$APPDIR/usr"

# Create a virtual-env-like structure inside AppDir
python3 -m venv "$APPDIR/usr/pyenv" --without-pip

APPDIR_PYTHON="$APPDIR/usr/pyenv/bin/python"

# Re-derive the Python version from the venv's own interpreter rather
# than trusting it matches the pre-creation python3 check above - this
# is what GRIX_DEST and the AppRun launcher's site-packages path below
# are built from, so it must be exactly right.
PYTHON_VERSION=$("$APPDIR_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "AppDir Python: $PYTHON_VERSION"

# Install pip into it. ensurepip only guarantees pip3/pip3.X binaries,
# not a plain "pip" - so everything below invokes pip via
# "python -m pip" instead of assuming a specific binary name exists.
"$APPDIR_PYTHON" -m ensurepip --upgrade
"$APPDIR_PYTHON" -m pip install --upgrade pip --quiet
"$APPDIR_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
"$APPDIR_PYTHON" -m pip install "$SCRIPT_DIR" --quiet

ok "Python environment built."

# ---------------------------------------------------------------------------
# Copy Grix source and assets into place
# ---------------------------------------------------------------------------

log "Copying Grix package..."
GRIX_SRC="$SCRIPT_DIR/grix"
GRIX_DEST="$APPDIR/usr/pyenv/lib/python${PYTHON_VERSION}/site-packages/grix"

# pip install already did this, but copy the assets folder explicitly
# to ensure all PNG files are included even in editable installs
if [[ -d "$GRIX_SRC/assets" ]]; then
    cp -r "$GRIX_SRC/assets" "$GRIX_DEST/"
    ok "Assets copied."
fi

# Same defensive copy for bundled plugins (e.g. the Griffin Suite
# integration) - package_data globs in setup.py should already cover
# this via pip install above, but copying explicitly avoids relying on
# that working perfectly across every setuptools version.
if [[ -d "$GRIX_SRC/plugins" ]]; then
    cp -r "$GRIX_SRC/plugins" "$GRIX_DEST/"
    ok "Bundled plugins copied."
fi

# ---------------------------------------------------------------------------
# Desktop entry and icon
# ---------------------------------------------------------------------------

log "Adding desktop entry and icon..."

cat > "$APPDIR/usr/share/applications/grix.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Grix
Comment=Friendly Linux system troubleshooter and learning companion
Exec=grix
Icon=grix
Terminal=false
Categories=System;Education;
EOF

cp "$APPDIR/usr/share/applications/grix.desktop" "$APPDIR/grix.desktop"

ICON_SRC="$GRIX_SRC/assets/grix_icon.png"
if [[ -f "$ICON_SRC" ]]; then
    cp "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/256x256/apps/grix.png"
    cp "$ICON_SRC" "$APPDIR/grix.png"
    ok "Icon installed."
else
    warn "Icon not found at $ICON_SRC"
fi

# ---------------------------------------------------------------------------
# Bundle PolicyKit integration (grix-helper + policy file)
# ---------------------------------------------------------------------------
# These can't be *used* directly from inside the AppImage (pkexec only
# trusts /usr/share/polkit-1/actions/ on the real filesystem), but
# bundling them means AppRun can offer to install them on first run
# without needing the user to separately download the source repo.

POLICYKIT_SRC="$SCRIPT_DIR/policykit"
if [[ -d "$POLICYKIT_SRC" ]]; then
    log "Bundling PolicyKit integration..."
    mkdir -p "$APPDIR/usr/share/grix/policykit"
    cp "$POLICYKIT_SRC/grix-helper" "$APPDIR/usr/share/grix/policykit/"
    cp "$POLICYKIT_SRC/com.griffinlinux.grix.policy" "$APPDIR/usr/share/grix/policykit/"
    chmod +x "$APPDIR/usr/share/grix/policykit/grix-helper"
    ok "PolicyKit integration bundled."
else
    warn "policykit/ directory not found - AppImage will fall back to bare pkexec/sudo for privileged actions."
fi

# ---------------------------------------------------------------------------
# AppRun launcher
# ---------------------------------------------------------------------------

log "Writing AppRun launcher..."

cat > "$APPDIR/AppRun" << EOF
#!/usr/bin/env bash
# Grix AppRun launcher
set -euo pipefail

HERE="\$(dirname "\$(readlink -f "\$0")")"
PYENV="\$HERE/usr/pyenv"
PYTHON="\$PYENV/bin/python"

# Qt platform plugin lookup
export QT_QPA_PLATFORM_PLUGIN_PATH="\$PYENV/lib/python${PYTHON_VERSION}/site-packages/PyQt6/Qt6/plugins/platforms"

# Fallback for systems without a compositor
export QT_QPA_PLATFORM="\${QT_QPA_PLATFORM:-xcb}"

# Allow overriding for Wayland
if [[ "\${XDG_SESSION_TYPE:-}" == "wayland" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi

# -----------------------------------------------------------------------
# Offer to install PolicyKit integration on first run
# -----------------------------------------------------------------------
# pkexec only trusts policy files installed at the real
# /usr/share/polkit-1/actions/ - it can't read them from inside this
# AppImage. Grix works fine without this (it falls back to bare
# pkexec, which still shows a graphical prompt, just with a generic
# message instead of a Grix-branded one and a narrower allowlist).
# This only ever asks once: a marker file records the user's choice
# either way, including "no", so declining doesn't nag on every launch.
#
# IMPORTANT: pkexec runs as root, and FUSE mounts (which is what "\$HERE"
# is, while running from an AppImage) block access from any user other
# than the one who created the mount - including root. This applies no
# matter what the file's own permission bits say. So the bundled files
# must be copied to a plain (non-FUSE) temp location FIRST, as the
# current user, and only THEN can pkexec (as root) read them.
GRIX_STATE_DIR="\$HOME/.local/share/grix"
POLKIT_MARKER="\$GRIX_STATE_DIR/.policykit_prompted"
HELPER_DEST="/usr/bin/grix-helper"
POLICY_DEST="/usr/share/polkit-1/actions/com.griffinlinux.grix.policy"
BUNDLED_POLICYKIT="\$HERE/usr/share/grix/policykit"

if [[ ! -f "\$POLKIT_MARKER" ]] && [[ -d "\$BUNDLED_POLICYKIT" ]] && command -v pkexec >/dev/null 2>&1; then
    mkdir -p "\$GRIX_STATE_DIR"
    if [[ ! -f "\$HELPER_DEST" ]] && [[ ! -f "\$POLICY_DEST" ]]; then
        if command -v zenity >/dev/null 2>&1; then
            zenity --question --title="Grix" --width=420 \\
                --text="Grix can install a small PolicyKit helper so administrator prompts show a Grix-branded dialog with a narrower, safer permission scope, instead of a generic one.\\n\\nThis is optional - Grix works fine either way. Install it now? (One-time admin prompt.)" \\
                && INSTALL_CHOICE=yes || INSTALL_CHOICE=no
        elif command -v kdialog >/dev/null 2>&1; then
            kdialog --title "Grix" --yesno \\
                "Grix can install a small PolicyKit helper for Grix-branded, narrower-scoped admin prompts. Optional - install now?" \\
                && INSTALL_CHOICE=yes || INSTALL_CHOICE=no
        else
            INSTALL_CHOICE=no
        fi

        if [[ "\${INSTALL_CHOICE:-no}" == "yes" ]]; then
            # Stage outside the FUSE mount first (see comment above) -
            # this temp dir lives on a normal filesystem (usually
            # tmpfs), which root CAN read.
            STAGING_DIR="\$(mktemp -d "\${TMPDIR:-/tmp}/grix-policykit.XXXXXX")"
            if cp "\$BUNDLED_POLICYKIT/grix-helper" "\$STAGING_DIR/grix-helper" 2>/dev/null \\
                && cp "\$BUNDLED_POLICYKIT/com.griffinlinux.grix.policy" "\$STAGING_DIR/com.griffinlinux.grix.policy" 2>/dev/null; then
                chmod 0755 "\$STAGING_DIR/grix-helper"
                chmod 0644 "\$STAGING_DIR/com.griffinlinux.grix.policy"
                chmod 0755 "\$STAGING_DIR"
                pkexec env \\
                    HELPER_SRC="\$STAGING_DIR/grix-helper" \\
                    POLICY_SRC="\$STAGING_DIR/com.griffinlinux.grix.policy" \\
                    sh -c 'install -m 0755 -o root -g root "\$HELPER_SRC" /usr/bin/grix-helper && install -m 0644 -o root -g root "\$POLICY_SRC" /usr/share/polkit-1/actions/com.griffinlinux.grix.policy' \\
                    || true
            fi
            rm -rf "\$STAGING_DIR"
        fi
    fi
    touch "\$POLKIT_MARKER"
fi

exec "\$PYTHON" -m grix.main "\$@"
EOF

chmod +x "$APPDIR/AppRun"
ok "AppRun written."

# ---------------------------------------------------------------------------
# Build the AppImage
# ---------------------------------------------------------------------------

log "Running appimagetool..."

mkdir -p "$OUTPUT_DIR"

ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "$OUTPUT_PATH" 2>&1

if [[ -f "$OUTPUT_PATH" ]]; then
    chmod +x "$OUTPUT_PATH"
    SIZE=$(du -sh "$OUTPUT_PATH" | cut -f1)
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  AppImage built successfully!${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Output : $OUTPUT_PATH"
    echo "  Size   : $SIZE"
    echo ""
    echo "  Run it :"
    echo "    chmod +x $OUTPUT_NAME"
    echo "    ./$OUTPUT_NAME"
    echo ""
else
    die "appimagetool ran but no output file was created."
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

log "Cleaning up temporary AppDir..."
rm -rf "$APPDIR"
ok "Done."
