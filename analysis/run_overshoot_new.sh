#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POST_DIR="$(cd "$DIR/../post-processing" && pwd)"

source "$POST_DIR/venv/bin/activate"

DATA_ROOT="${DATA_ROOT:-/mnt/disks/wiemip-data/re-run-overshoot}"
INPUT_SUBDIR="${INPUT_SUBDIR:-filtered_wiemip_output}"
OUTDIR="${OUTDIR:-$DATA_ROOT/figures}"
RUN_MASK="${RUN_MASK:-$POST_DIR/run-mask2.nc}"
SCENARIOS="${SCENARIOS:-historic l}"
AGG="${AGG:-mean}"
STITCH="${STITCH:-0}"

mkdir -p "$OUTDIR"

PLOT_SCRIPT="$DIR/plot_overshoot_new.py"
EXTRA_ARGS=()
if [[ "$STITCH" == "1" || "$STITCH" == "true" ]]; then
  EXTRA_ARGS+=(--stitch)
fi
if [[ -f "$RUN_MASK" ]]; then
  EXTRA_ARGS+=(--run-mask "$RUN_MASK")
fi

echo "plot_overshoot_new batch"
echo "  DATA_ROOT=$DATA_ROOT"
echo "  INPUT_SUBDIR=$INPUT_SUBDIR"
echo "  SCENARIOS=$SCENARIOS"
echo "  OUTDIR=$OUTDIR"
echo "  RUN_MASK=$RUN_MASK"
echo ""

# List of variables and their frequencies
VARS=(
"alt yr"
"cCwd yr"
"cSoil yr"
"cSoilAbove1m yr"
"cSoilBelow1m yr"
"cVeg yr"
"cVegpft yr"
"evapotrans mon"
"fFireCveg mon"
"fNnetmin mon"
"ffirepeatTotal mon"
"gpp mon"
"gpppft mon"
"lai mon"
"laipft mon"
"mrso mon"
"nInorgSoil yr"
"nOrgSoil yr"
"nVeg yr"
"npp mon"
"npppft mon"
"ra mon"
"rh mon"
"snowDepth mon"
"swe mon"
"tveg mon"
"wetCH4 mon"
"wtd mon"
)

for item in "${VARS[@]}"; do
    var=$(echo "$item" | awk '{print $1}')
    freq=$(echo "$item" | awk '{print $2}')

    echo "Running analysis for $var ($freq)..."
    python "$PLOT_SCRIPT" \
        --var "$var" \
        --freq "$freq" \
        --agg "$AGG" \
        --data-root "$DATA_ROOT" \
        --input-subdir "$INPUT_SUBDIR" \
        --scenarios $SCENARIOS \
        --outdir "$OUTDIR" \
        "${EXTRA_ARGS[@]}"
done

echo "Done. Figures in $OUTDIR"
