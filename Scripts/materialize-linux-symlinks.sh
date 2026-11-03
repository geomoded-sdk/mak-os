#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TREE="$ROOT/Kernel/linux-6.1"

# Windows checkouts cannot create every symlink from the Linux tarball. Read
# the official archive's link table and materialize each link after extraction.
cat "$ROOT"/Kernel/vendor/linux-6.1.tar.xz.part-* \
  | tar -tJv 2>/dev/null \
  | awk '$1 ~ /^l/ { p=$6; t=$8; sub(/^linux-6.1\//, "", p); print p "\t" t }' \
  | while IFS=$'\t' read -r path target; do
      dir="$(dirname "$path")"
      resolved="$(realpath -m "$dir/$target")"
      source="$TREE/$resolved"
      destination="$TREE/$path"
      if [ -d "$source" ]; then
        mkdir -p "$destination"
        cp -a "$source/." "$destination/"
      elif [ -f "$source" ]; then
        mkdir -p "$(dirname "$destination")"
        cp -f "$source" "$destination"
      fi
    done
