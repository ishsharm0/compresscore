#!/bin/bash
# CompressCore Installer
# Usage: curl -sSL https://raw.githubusercontent.com/ishsharm0/compresscore/main/install.sh | bash

set -e

REPO="https://github.com/ishsharm0/compresscore.git"

BOLD='\033[1m'
GREEN='\033[32m'
BLUE='\033[34m'
YELLOW='\033[33m'
RED='\033[31m'
RESET='\033[0m'

info() { echo -e "${BLUE}ℹ${RESET} $1"; }
success() { echo -e "${GREEN}✓${RESET} $1"; }
warn() { echo -e "${YELLOW}⚠${RESET} $1"; }
error() { echo -e "${RED}✗${RESET} $1"; exit 1; }

echo -e "${BOLD}CompressCore Installer${RESET}\n"

# Check for Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 is required. Install it with: brew install python"
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Found Python $PYTHON_VERSION"

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    warn "FFmpeg not found. Install it with: brew install ffmpeg"
fi

# Determine shell config file
if [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

# Try pipx first (preferred)
if command -v pipx &> /dev/null; then
    info "Installing with pipx from GitHub..."
    pipx install "git+${REPO}" 2>/dev/null || pipx install --force "git+${REPO}"
    success "Installed with pipx"
    
    # Ensure pipx bin is in PATH
    PIPX_BIN="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$PIPX_BIN:"* ]]; then
        echo "export PATH=\"$PIPX_BIN:\$PATH\"" >> "$SHELL_RC"
        export PATH="$PIPX_BIN:$PATH"
        info "Added $PIPX_BIN to PATH in $SHELL_RC"
    fi
else
    info "Installing with pip from GitHub..."
    pip3 install --user "git+${REPO}"
    success "Installed with pip"
    
    # Add Python user bin to PATH if needed
    PYTHON_BIN="$HOME/Library/Python/$PYTHON_VERSION/bin"
    if [[ ! -d "$PYTHON_BIN" ]]; then
        # Linux fallback
        PYTHON_BIN="$HOME/.local/bin"
    fi
    
    if [[ ":$PATH:" != *":$PYTHON_BIN:"* ]]; then
        echo "export PATH=\"$PYTHON_BIN:\$PATH\"" >> "$SHELL_RC"
        export PATH="$PYTHON_BIN:$PATH"
        info "Added $PYTHON_BIN to PATH in $SHELL_RC"
    fi
fi

# Verify installation
echo ""
if command -v cpc &> /dev/null; then
    success "Installation complete!"
    echo ""
    cpc --version
    echo ""
    echo -e "Run ${BOLD}cpc --help${RESET} to get started."
    echo -e "Or try: ${BOLD}cpc video.mov -t 8MB${RESET}"
else
    warn "Installation complete, but 'cpc' not in current PATH."
    echo ""
    echo -e "Restart your terminal or run: ${BOLD}source $SHELL_RC${RESET}"
    echo -e "Then try: ${BOLD}cpc --help${RESET}"
fi
