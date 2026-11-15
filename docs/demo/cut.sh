#!/bin/bash
# cut.sh <src.mp4> <name> <duration_s> [extra_skip_s]
# Finds the white flash frame the scene script draws at its start, then cuts
# <duration_s> seconds after it into docs/demo/<name>.gif (960 px, 12 fps).
set -e
SRC="$1"; NAME="$2"; DUR="$3"; SKIP="${4:-0.5}"
FPS="${FPS:-12}"; COLORS="${COLORS:-160}"; DITHER="${DITHER:-bayer:bayer_scale=4}"; SUFFIX="${SUFFIX:-}"; WIDTH="${WIDTH:-960}"
OUT="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT/raw"
[ "$SRC" -ef "$OUT/raw/$NAME.mp4" ] || cp "$SRC" "$OUT/raw/$NAME.mp4"
T=$(ffmpeg -v error -i "$OUT/raw/$NAME.mp4" -vf "scale=64:-1,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null - 2>/dev/null \
  | awk '/pts_time/{split($0,a,"pts_time:"); t=a[2]} /YAVG/{split($0,b,"="); if (b[2]>180 && !found) {print t; found=1}}')
if [ -z "$T" ]; then echo "no flash found"; exit 1; fi
START=$(python3 -c "print(round($T + $SKIP, 2))")
ffmpeg -v error -y -ss "$START" -t "$DUR" -i "$OUT/raw/$NAME.mp4" \
  -vf "fps=$FPS,scale=$WIDTH:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=$COLORS:stats_mode=diff[p];[b][p]paletteuse=dither=$DITHER:diff_mode=rectangle" \
  "$OUT/$NAME$SUFFIX.gif"
echo "flash at $T, cut from $START for $DUR s -> $(du -h "$OUT/$NAME$SUFFIX.gif" | cut -f1)"
