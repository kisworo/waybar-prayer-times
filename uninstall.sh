#!/usr/bin/env bash
# ==============================================================================
# Waybar Prayer Times & Adzan Countdown — Uninstaller
# ==============================================================================

set -euo pipefail

BIN_TARGET="$HOME/.local/bin/waybar-prayer-times"
CACHE_TARGET="$HOME/.cache/waybar-prayer-times.json"
CONFIG_TARGET="$HOME/.config/waybar-prayer.conf"

echo "Menghapus waybar-prayer-times..."

rm -f "$BIN_TARGET"
rm -f "$CACHE_TARGET"
rm -f "$CONFIG_TARGET"

echo "✓ File script dan cache berhasil dihapus."
echo "ℹ Silakan hapus 'custom/prayer' dari konfigurasi Waybar Anda jika sudah tidak digunakan."
