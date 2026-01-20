#!/usr/bin/env bash
#
# Agent Zero CLI - One-liner Installer
# Usage: curl -sSL https://raw.githubusercontent.com/vizi2000/agentzero-cli/main/scripts/install.sh | bash
#
set -e

REPO="vizi2000/agentzero-cli"
INSTALL_DIR="$HOME/.local/share/agentzero"
BIN_DIR="$HOME/.local/bin"

echo "Agent Zero CLI Installer"
echo "========================"
echo ""

# Check Python version
check_python() {
    if command -v python3 &> /dev/null; then
        PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
            echo "[OK] Python $PY_VERSION found"
            return 0
        fi
    fi
    
    echo "[ERROR] Python 3.10+ required"
    echo "Install with: brew install python@3.12 (macOS) or apt install python3 (Linux)"
    exit 1
}

# Check git
check_git() {
    if command -v git &> /dev/null; then
        echo "[OK] Git found"
        return 0
    fi
    
    echo "[ERROR] Git required"
    echo "Install with: brew install git (macOS) or apt install git (Linux)"
    exit 1
}

# Create directories
setup_dirs() {
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    echo "[OK] Directories created"
}

# Clone or update repository
clone_repo() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull --ff-only
    else
        echo "Cloning repository..."
        rm -rf "$INSTALL_DIR"
        git clone --depth 1 "https://github.com/$REPO.git" "$INSTALL_DIR"
    fi
    echo "[OK] Repository ready"
}

# Setup Python virtual environment
setup_venv() {
    cd "$INSTALL_DIR"
    
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    deactivate
    
    echo "[OK] Dependencies installed"
}

# Create launcher script
create_launcher() {
    cat > "$BIN_DIR/a0" << 'EOF'
#!/usr/bin/env bash
INSTALL_DIR="$HOME/.local/share/agentzero"
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py "$@"
EOF
    
    chmod +x "$BIN_DIR/a0"
    
    # Also create agentzerocli alias
    ln -sf "$BIN_DIR/a0" "$BIN_DIR/agentzero"
    
    echo "[OK] Launcher created: $BIN_DIR/a0"
}

# Add to PATH if needed
setup_path() {
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo ""
        echo "Add to your shell config (~/.bashrc, ~/.zshrc):"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    fi
}

# Create .env template
setup_env() {
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env" 2>/dev/null || true
        echo ""
        echo "Configure your API key:"
        echo "  echo 'OPENROUTER_API_KEY=sk-or-...' >> $INSTALL_DIR/.env"
        echo ""
    fi
}

# Main installation
main() {
    check_python
    check_git
    setup_dirs
    clone_repo
    setup_venv
    create_launcher
    setup_path
    setup_env
    
    echo ""
    echo "Installation complete!"
    echo ""
    echo "Run Agent Zero CLI:"
    echo "  a0"
    echo ""
    echo "Or with full path:"
    echo "  $BIN_DIR/a0"
    echo ""
}

main
