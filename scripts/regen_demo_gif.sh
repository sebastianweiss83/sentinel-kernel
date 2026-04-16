#!/usr/bin/env bash
# Regenerate the hero screencast for docs/samples/sentinel-demo.gif.
#
# Requires:
#   brew install asciinema agg    # macOS
#   (or apt install asciinema; cargo install --git https://github.com/asciinema/agg)
#
# Output:
#   docs/samples/sentinel-demo.gif    — animated screencast
#
# The README references docs/samples/sentinel-demo.svg as the placeholder
# and docs/samples/sentinel-demo.gif once this script has run. Swap the
# README img src from .svg → .gif after the first successful run.
set -euo pipefail

command -v asciinema >/dev/null || { echo "Install asciinema first: brew install asciinema" >&2; exit 1; }
command -v agg       >/dev/null || { echo "Install agg first: cargo install --git https://github.com/asciinema/agg" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d -t sentinel-demo-gif-XXXX)"
trap 'rm -rf "$WORK"' EXIT

pushd "$WORK" >/dev/null
echo "→ Recording sentinel demo (20 s target, Ctrl-D when done)"
asciinema rec demo.cast -c "python3 -m sentinel demo --no-kill-switch" --overwrite

echo "→ Rendering GIF"
agg \
  --theme monokai \
  --font-size 14 \
  --cols 84 --rows 28 \
  --speed 1.2 \
  demo.cast "$HERE/docs/samples/sentinel-demo.gif"

popd >/dev/null

echo
echo "✓ Wrote $HERE/docs/samples/sentinel-demo.gif"
echo "  Next: update README.md to reference sentinel-demo.gif instead of sentinel-demo.svg"
