#!/usr/bin/env bash
# ==============================================================================
# Waybar Prayer Times & Adzan Countdown — Installer
# Author: Kisworo (https://github.com/kisworo)
# License: MIT
# ==============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================================${NC}"
echo -e "${GREEN}  🕌 Waybar Prayer Times & Adzan Countdown Installer ${NC}"
echo -e "${BLUE}=====================================================${NC}"

# 1. Check Python3
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] Python 3 tidak ditemukan. Silakan install python3 terlebih dahulu.${NC}"
    exit 1
fi

# 2. Setup directories
BIN_DIR="$HOME/.local/bin"
WAYBAR_DIR="$HOME/.config/waybar"
SCRIPT_TARGET="$BIN_DIR/waybar-prayer-times"

mkdir -p "$BIN_DIR"
mkdir -p "$WAYBAR_DIR"

# Download / copy script
echo -e "${YELLOW}[1/4] Menginstal script ke $SCRIPT_TARGET...${NC}"
if [ -f "$(dirname "$0")/prayer_times.py" ]; then
    cp "$(dirname "$0")/prayer_times.py" "$SCRIPT_TARGET"
else
    curl -sSL "https://raw.githubusercontent.com/kisworo/waybar-prayer-times/main/prayer_times.py" -o "$SCRIPT_TARGET"
fi
chmod +x "$SCRIPT_TARGET"
echo -e "${GREEN}✓ Script berhasil diinstal!${NC}"

# 3. Test script
echo -e "${YELLOW}[2/4] Menguji deteksi lokasi & jadwal...${NC}"
TEST_OUTPUT=$("$SCRIPT_TARGET" --list 2>&1 || true)
echo -e "${BLUE}$TEST_OUTPUT${NC}"

# 4. Waybar Module Configuration
echo -e "${YELLOW}[3/4] Menyiapkan konfigurasi Waybar...${NC}"

MODULE_SNIPPET='
"custom/prayer": {
    "format": "{}",
    "exec": "'"$SCRIPT_TARGET"'",
    "interval": 60,
    "return-type": "json",
    "on-click": "'"$SCRIPT_TARGET"' --notify",
    "on-click-right": "'"$SCRIPT_TARGET"' --force",
    "tooltip": true
}'

if [ -f "$WAYBAR_DIR/UserModules" ]; then
    if ! grep -q "custom/prayer" "$WAYBAR_DIR/UserModules"; then
        # Insert before last closing brace in UserModules
        sed -i '$ s/}/,'"$MODULE_SNIPPET"'\n}/' "$WAYBAR_DIR/UserModules"
        echo -e "${GREEN}✓ Modul otomatis didaftarkan ke $WAYBAR_DIR/UserModules${NC}"
    else
        echo -e "${BLUE}ℹ Modul custom/prayer sudah ada di $WAYBAR_DIR/UserModules${NC}"
    fi
fi

# 5. Styling
CSS_SNIPPET='
/* Waybar Prayer Times */
#custom-prayer {
    padding: 0 8px;
    font-weight: bold;
}
#custom-prayer.warning {
    color: #f3f809;
}
#custom-prayer.adzan {
    color: #ff5555;
}
'

if [ -f "$WAYBAR_DIR/style.css" ]; then
    if ! grep -q "#custom-prayer" "$WAYBAR_DIR/style.css"; then
        echo -e "$CSS_SNIPPET" >> "$WAYBAR_DIR/style.css"
        echo -e "${GREEN}✓ Style CSS ditambahkan ke $WAYBAR_DIR/style.css${NC}"
    fi
fi

# 6. Reload Waybar
echo -e "${YELLOW}[4/4] Memperbarui Waybar...${NC}"
if pidof waybar >/dev/null 2>&1; then
    killall waybar 2>/dev/null || true
    sleep 0.5
    nohup waybar >/dev/null 2>&1 & disown
    echo -e "${GREEN}✓ Waybar berhasil direload!${NC}"
fi

echo ""
echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN}  🎉 Instalasi Selesai!                             ${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo -e "Catatan penting:"
echo -e "1. Tambahkan ${YELLOW}\"custom/prayer\"${NC} ke dalam ${BLUE}\"modules-left\"${NC}, ${BLUE}\"modules-center\"${NC}, atau ${BLUE}\"modules-right\"${NC} pada file config Waybar Anda."
echo -e "2. Untuk tes jadwal langsung di terminal: ketik ${YELLOW}waybar-prayer-times --list${NC}"
echo ""
