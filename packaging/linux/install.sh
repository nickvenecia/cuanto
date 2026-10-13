#!/usr/bin/env bash
# Installs Cuanto for the current user and adds it to your app menu.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
# The program goes in ~/.local/opt. Your budgets live in ~/.local/share/cuanto: never install there.
DEST="$HOME/.local/opt/cuanto"
DATA="${CUANTO_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/cuanto}"
# never let the program folder and the data folder overlap, either way round
case "$DEST/" in "$DATA"/*) echo "Refusing to install inside Cuanto's data folder ($DATA)."; exit 1 ;; esac
case "$DATA/" in "$DEST"/*) echo "Cuanto's data folder ($DATA) is inside $DEST. Move it first."; exit 1 ;; esac
if [ -e "$DEST/rates.json" ] || [ -d "$DEST/budgets" ]; then
  echo "$DEST holds Cuanto data, not the program. Move it first."; exit 1
fi
rm -rf "$DEST"
mkdir -p "$DEST" "$HOME/.local/share/applications"
cp -R "$SRC"/. "$DEST"/
# the menu entry: the path quoted, and escaped for sed (a home folder can hold spaces, | or &)
SAFE_DEST=$(printf '%s' "$DEST" | sed -e 's/[\\/&|]/\\&/g')
sed "s|CUANTO_DIR|$SAFE_DEST|g" "$SRC/cuanto.desktop" > "$HOME/.local/share/applications/cuanto.desktop"
chmod +x "$DEST/Cuanto"
echo "Cuanto installed. Find it in your app menu, or run: $DEST/Cuanto"
