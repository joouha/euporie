#!/usr/bin/env bash
#
# Generate thumbnail files for all gallery images.
#
# For every gallery image in docs/_static/images/ named `gallery.*.webp`
# (excluding existing `.thumb.webp` thumbnails), create a corresponding
# `.thumb.webp` file resized to a maximum width of 400px.
#
# Requires ImageMagick (`magick` or `convert`).

set -euo pipefail

IMAGE_DIR="docs/_static/images"
THUMB_WIDTH=400

# Pick the available ImageMagick command
if command -v magick >/dev/null 2>&1; then
    CONVERT="magick"
elif command -v convert >/dev/null 2>&1; then
    CONVERT="convert"
else
    echo "Error: ImageMagick ('magick' or 'convert') is not installed." >&2
    exit 1
fi

shopt -s nullglob

for src in "$IMAGE_DIR"/gallery.*.webp; do
    # Skip files that are already thumbnails
    case "$src" in
        *.thumb.webp) continue ;;
    esac

    # Build the thumbnail path: foo.webp -> foo.thumb.webp
    thumb="${src%.webp}.thumb.webp"

    # Only generate if missing or the source is newer
    if [[ ! -f "$thumb" || "$src" -nt "$thumb" ]]; then
        echo "Generating thumbnail: $thumb"
        "$CONVERT" "$src" -resize "${THUMB_WIDTH}x>" "$thumb"
    else
        echo "Up to date: $thumb"
    fi
done

echo "Done."
