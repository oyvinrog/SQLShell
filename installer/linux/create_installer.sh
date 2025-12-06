#!/bin/bash
#
# SQLShell Linux Installer Creator
# Creates a self-extracting installer using makeself
#
# Requirements:
#   - makeself (apt install makeself)
#   - Built SQLShell in dist/SQLShell/
#
# Usage: ./create_installer.sh

set -e

APP_NAME="SQLShell"
APP_VERSION="0.3.3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BUILD_DIR="$PROJECT_ROOT/dist/$APP_NAME"
OUTPUT_DIR="$PROJECT_ROOT/dist"
INSTALLER_NAME="${APP_NAME}-${APP_VERSION}-linux-x64-installer.run"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            SQLShell Linux Installer Creator                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

# Check if makeself is installed
if ! command -v makeself &> /dev/null; then
    echo "Error: makeself is not installed."
    echo "Install it with: sudo apt install makeself"
    exit 1
fi

# Check if build exists
if [ ! -d "$BUILD_DIR" ]; then
    echo "Error: Build directory not found at $BUILD_DIR"
    echo "Please run 'python build.py' first."
    exit 1
fi

# Create staging directory
STAGING_DIR=$(mktemp -d)
trap "rm -rf $STAGING_DIR" EXIT

echo "Creating installer package..."

# Copy application files
cp -r "$BUILD_DIR" "$STAGING_DIR/$APP_NAME"

# Create installation script
cat > "$STAGING_DIR/install.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
#
# SQLShell Installation Script
#

APP_NAME="SQLShell"
DEFAULT_INSTALL_DIR="/opt/sqlshell"
BIN_LINK="/usr/local/bin/sqlshell"
DESKTOP_FILE="/usr/share/applications/sqlshell.desktop"
ICON_DIR="/usr/share/icons/hicolor/256x256/apps"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   SQLShell Installer                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Running without root privileges.${NC}"
    echo "Installing to user directory instead."
    DEFAULT_INSTALL_DIR="$HOME/.local/share/sqlshell"
    BIN_LINK="$HOME/.local/bin/sqlshell"
    DESKTOP_FILE="$HOME/.local/share/applications/sqlshell.desktop"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
    
    # Ensure directories exist
    mkdir -p "$HOME/.local/bin"
    mkdir -p "$HOME/.local/share/applications"
    mkdir -p "$ICON_DIR"
fi

# Ask for installation directory
read -p "Install directory [$DEFAULT_INSTALL_DIR]: " INSTALL_DIR
INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

echo
echo "Installing to: $INSTALL_DIR"
echo

# Remove old installation if exists
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing previous installation..."
    rm -rf "$INSTALL_DIR"
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy files
echo "Copying files..."
cp -r "$APP_NAME"/* "$INSTALL_DIR/"

# Make executable
chmod +x "$INSTALL_DIR/$APP_NAME"

# Create symlink
echo "Creating command-line launcher..."
ln -sf "$INSTALL_DIR/$APP_NAME" "$BIN_LINK"

# Copy icon if exists
if [ -f "$INSTALL_DIR/sqlshell/resources/icon.png" ]; then
    mkdir -p "$ICON_DIR"
    cp "$INSTALL_DIR/sqlshell/resources/icon.png" "$ICON_DIR/sqlshell.png"
elif [ -f "icon.png" ]; then
    mkdir -p "$ICON_DIR"
    cp "icon.png" "$ICON_DIR/sqlshell.png"
fi

# Create desktop entry
echo "Creating desktop entry..."
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=SQLShell
Comment=A powerful SQL shell with GUI interface for data analysis
Exec=$INSTALL_DIR/$APP_NAME
Icon=sqlshell
Categories=Development;Database;
Terminal=false
StartupWMClass=SQLShell
EOF

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$(dirname "$DESKTOP_FILE")" 2>/dev/null || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t "$(dirname "$(dirname "$ICON_DIR")")" 2>/dev/null || true
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                          ║"
echo "╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo "You can start SQLShell by:"
echo "  1. Running 'sqlshell' from the terminal"
echo "  2. Finding it in your application menu"
echo "  3. Running directly: $INSTALL_DIR/$APP_NAME"
echo
INSTALL_SCRIPT

chmod +x "$STAGING_DIR/install.sh"

# Create uninstall script
cat > "$STAGING_DIR/$APP_NAME/uninstall.sh" << 'UNINSTALL_SCRIPT'
#!/bin/bash
#
# SQLShell Uninstaller
#

echo "SQLShell Uninstaller"
echo "===================="
echo

# Determine installation type
if [ -L "/usr/local/bin/sqlshell" ]; then
    INSTALL_DIR=$(dirname "$(readlink -f /usr/local/bin/sqlshell)")
    BIN_LINK="/usr/local/bin/sqlshell"
    DESKTOP_FILE="/usr/share/applications/sqlshell.desktop"
    ICON_FILE="/usr/share/icons/hicolor/256x256/apps/sqlshell.png"
    
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root to uninstall system-wide installation"
        exit 1
    fi
elif [ -L "$HOME/.local/bin/sqlshell" ]; then
    INSTALL_DIR=$(dirname "$(readlink -f $HOME/.local/bin/sqlshell)")
    BIN_LINK="$HOME/.local/bin/sqlshell"
    DESKTOP_FILE="$HOME/.local/share/applications/sqlshell.desktop"
    ICON_FILE="$HOME/.local/share/icons/hicolor/256x256/apps/sqlshell.png"
else
    echo "SQLShell installation not found."
    exit 1
fi

read -p "Remove SQLShell from $INSTALL_DIR? [y/N]: " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo "Removing SQLShell..."

rm -f "$BIN_LINK"
rm -f "$DESKTOP_FILE"
rm -f "$ICON_FILE"
rm -rf "$INSTALL_DIR"

echo "SQLShell has been removed."
UNINSTALL_SCRIPT

chmod +x "$STAGING_DIR/$APP_NAME/uninstall.sh"

# Copy icon to staging
if [ -f "$PROJECT_ROOT/sqlshell/resources/icon.png" ]; then
    cp "$PROJECT_ROOT/sqlshell/resources/icon.png" "$STAGING_DIR/icon.png"
fi

# Create the self-extracting installer
echo "Creating self-extracting installer..."
makeself --notemp "$STAGING_DIR" "$OUTPUT_DIR/$INSTALLER_NAME" "$APP_NAME Installer" "./install.sh"

echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Installer Created!                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo
echo "Output: $OUTPUT_DIR/$INSTALLER_NAME"
echo
echo "To install, run:"
echo "  chmod +x $INSTALLER_NAME"
echo "  ./$INSTALLER_NAME"
echo
echo "Or with sudo for system-wide installation:"
echo "  sudo ./$INSTALLER_NAME"
echo

