#!/usr/bin/env bash
# =============================================================================
# build.sh — IPTVShows PyQt6 app builder
# Usage:
#   ./build.sh            — build only
#   ./build.sh install    — build + install to ~/.local/bin + desktop entry
#   ./build.sh uninstall  — remove installed binary + desktop entry
# =============================================================================

set -e

APP_NAME="iptvshows"
APP_DISPLAY_NAME="IPTV Shows"
APP_COMMENT="Browse and stream IPTV shows via Xtream Codes"
APP_CATEGORY="AudioVideo;"
ENTRY="main.py"
OUT_DIR="dist"
BINARY_DIR="binary"

INSTALL_BIN="$HOME/.local/bin"
INSTALL_DESKTOP="$HOME/.local/share/applications"
DESKTOP_FILE="$INSTALL_DESKTOP/${APP_NAME}.desktop"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ==============================================================================
# UNINSTALL
# ==============================================================================
do_uninstall() {
    echo -e "${CYAN}"
    echo "=================================================="
    echo "  IPTVShows — Uninstall"
    echo "=================================================="
    echo -e "${NC}"

    local removed=0

    if [ -f "$INSTALL_BIN/$APP_NAME" ]; then
        rm -f "$INSTALL_BIN/$APP_NAME"
        success "Removed binary: $INSTALL_BIN/$APP_NAME"
        removed=1
    else
        warn "Binary not found at $INSTALL_BIN/$APP_NAME (skipping)"
    fi

    if [ -f "$DESKTOP_FILE" ]; then
        rm -f "$DESKTOP_FILE"
        success "Removed desktop entry: $DESKTOP_FILE"
        # Refresh desktop database
        if command -v update-desktop-database &>/dev/null; then
            update-desktop-database "$INSTALL_DESKTOP" 2>/dev/null || true
        fi
        # KDE-specific refresh
        if command -v kbuildsycoca6 &>/dev/null; then
            kbuildsycoca6 --noincremental 2>/dev/null || true
        elif command -v kbuildsycoca5 &>/dev/null; then
            kbuildsycoca5 --noincremental 2>/dev/null || true
        fi
        removed=1
    else
        warn "Desktop entry not found at $DESKTOP_FILE (skipping)"
    fi

    if [ "$removed" -eq 0 ]; then
        warn "Nothing to uninstall."
    else
        echo ""
        success "Uninstall complete."
    fi
    exit 0
}

# ==============================================================================
# INSTALL (after binary is built)
# ==============================================================================
do_install() {
    echo ""
    echo -e "${CYAN}=================================================="
    echo "  Installing IPTVShows"
    echo -e "==================================================${NC}"

    # 1. Copy binary
    mkdir -p "$INSTALL_BIN"
    cp "$BINARY_DIR/$APP_NAME" "$INSTALL_BIN/$APP_NAME"
    chmod +x "$INSTALL_BIN/$APP_NAME"
    success "Binary installed: $INSTALL_BIN/$APP_NAME"

    # 2. Create .desktop entry
    mkdir -p "$INSTALL_DESKTOP"
    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_DISPLAY_NAME}
Comment=${APP_COMMENT}
Exec=${INSTALL_BIN}/${APP_NAME}
Icon=video-television
Terminal=false
Categories=${APP_CATEGORY}
StartupNotify=true
EOF
    chmod +x "$DESKTOP_FILE"
    success "Desktop entry created: $DESKTOP_FILE"

    # 3. Refresh desktop database
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$INSTALL_DESKTOP" 2>/dev/null || true
    fi
    # KDE-specific refresh
    if command -v kbuildsycoca6 &>/dev/null; then
        kbuildsycoca6 --noincremental 2>/dev/null || true
    elif command -v kbuildsycoca5 &>/dev/null; then
        kbuildsycoca5 --noincremental 2>/dev/null || true
    fi
    # XFCE-specific refresh
    if command -v xfce4-panel &>/dev/null; then
        rm -rf ~/.cache/menus 2>/dev/null || true
        xfce4-panel --restart 2>/dev/null || true
    fi

    echo ""
    echo -e "${GREEN}=================================================="
    echo "  Install Complete!"
    echo "=================================================="
    echo -e "${NC}"
    echo -e "  Binary  : ${CYAN}$INSTALL_BIN/$APP_NAME${NC}"
    echo -e "  Desktop : ${CYAN}$DESKTOP_FILE${NC}"
    echo -e "  Run it  : ${YELLOW}$APP_NAME${NC}"
    echo ""
}

# ==============================================================================
# Handle uninstall before anything else
# ==============================================================================
if [[ "${1}" == "uninstall" ]]; then
    do_uninstall
fi

# ==============================================================================
# BUILD
# ==============================================================================
echo -e "${CYAN}"
echo "=================================================="
echo "  IPTVShows — PyQt6 Build Script"
echo "=================================================="
echo -e "${NC}"

# ------------------------------------------------------------------------------
# 1. Locate Python
# ------------------------------------------------------------------------------
info "Detecting Python environment..."

if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
    PYINSTALLER=".venv/bin/pyinstaller"
    info "Using venv: .venv"
elif [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
    PYINSTALLER="venv/bin/pyinstaller"
    info "Using venv: venv"
else
    PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
    PYINSTALLER=$(which pyinstaller 2>/dev/null || echo "")
    if [ -z "$PYTHON" ]; then
        error "No Python found. Install Python 3 or create a venv."
    fi
    info "Using system Python: $PYTHON"
fi

PYTHON_VERSION=$("$PYTHON" --version 2>&1)
success "Found: $PYTHON_VERSION"

# ------------------------------------------------------------------------------
# 2. Check PyInstaller
# ------------------------------------------------------------------------------
if [ -z "$PYINSTALLER" ] || [ ! -f "$PYINSTALLER" ]; then
    PYINSTALLER=$("$PYTHON" -m PyInstaller --version &>/dev/null && echo "$PYTHON -m PyInstaller" || echo "")
fi

if [ -z "$PYINSTALLER" ]; then
    warn "PyInstaller not found. Installing..."
    "$PYTHON" -m pip install pyinstaller --break-system-packages
    PYINSTALLER="$PYTHON -m PyInstaller"
fi

success "PyInstaller ready"

# ------------------------------------------------------------------------------
# 3. Check entry point
# ------------------------------------------------------------------------------
[ -f "$ENTRY" ] || error "Entry point '$ENTRY' not found. Run this script from your project root."

# ------------------------------------------------------------------------------
# 4. Clean previous build
# ------------------------------------------------------------------------------
info "Cleaning previous build..."
rm -rf build/ "$OUT_DIR"/ "$APP_NAME".spec
success "Cleaned"

# ------------------------------------------------------------------------------
# 5. Run PyInstaller
# ------------------------------------------------------------------------------
info "Building binary (this may take a minute)..."

$PYINSTALLER \
    --onefile \
    --name "$APP_NAME" \
    --noconfirm \
    --clean \
    --icon "iptvshow.ico" \
    \
    `# --- PyQt6 core ---` \
    --hidden-import PyQt6 \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import PyQt6.QtNetwork \
    --hidden-import PyQt6.QtMultimedia \
    --hidden-import PyQt6.sip \
    \
    `# --- PyQt6 submodules ---` \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtDBus \
    \
    `# --- requests / urllib ---` \
    --hidden-import requests \
    --hidden-import requests.adapters \
    --hidden-import requests.auth \
    --hidden-import requests.cookies \
    --hidden-import requests.exceptions \
    --hidden-import urllib3 \
    --hidden-import urllib3.util.retry \
    --hidden-import urllib3.util.timeout \
    \
    `# --- sqlite3 / FTS5 ---` \
    --hidden-import sqlite3 \
    \
    `# --- standard lib ---` \
    --hidden-import json \
    --hidden-import threading \
    --hidden-import datetime \
    --hidden-import hashlib \
    --hidden-import base64 \
    --hidden-import re \
    \
    "$ENTRY"

success "PyInstaller finished"

# ------------------------------------------------------------------------------
# 6. Copy binary to binary/ dir
# ------------------------------------------------------------------------------
info "Copying binary to $BINARY_DIR/..."
mkdir -p "$BINARY_DIR"
cp "$OUT_DIR/$APP_NAME" "$BINARY_DIR/$APP_NAME"
chmod +x "$BINARY_DIR/$APP_NAME"

success "Binary ready: $BINARY_DIR/$APP_NAME"

# ------------------------------------------------------------------------------
# 7. Summary / install
# ------------------------------------------------------------------------------
BINARY_SIZE=$(du -sh "$BINARY_DIR/$APP_NAME" | cut -f1)
echo ""
echo -e "${GREEN}=================================================="
echo "  Build Complete!"
echo "=================================================="
echo -e "${NC}"
echo -e "  Binary : ${CYAN}$BINARY_DIR/$APP_NAME${NC}"
echo -e "  Size   : ${CYAN}$BINARY_SIZE${NC}"
echo ""

if [[ "${1}" == "install" ]]; then
    do_install
else
    echo -e "  Run it  : ${YELLOW}./$BINARY_DIR/$APP_NAME${NC}"
    echo -e "  Install : ${YELLOW}./build.sh install${NC}"
    echo ""
fi
