#!/bin/bash
# Full overshoot post-processing: merge/convert/filter -> coords -> layer
# geometry -> time/coord fix.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
export WIEMIP_CONFIG=config_overshoot.sh
source "$DIR/$WIEMIP_CONFIG"
BASE="$OUTPUT_DIR"
MASK="$DIR/run-mask2.nc"

mkdir -p "$BASE" /mnt/disks/wiemip-data/tmp
LOG="$BASE/run_overshoot_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
echo "=== overshoot post-processing $(date -Is)  OUTPUT_DIR=$BASE ==="

echo "=== 1. merge / convert / filter (setup.sh) ==="
./setup.sh
source venv/bin/activate

echo "=== 2. add coords -> filtered_with_coord ==="
for case_path in "$BASE"/DVM-DOS-TEM_*; do
  if [[ -d "${case_path}/filtered_wiemip_output" ]]; then
    echo "Coords: $(basename "$case_path")"
    python process_all_cases_add_coords.py \
      --work-root "${case_path}/filtered_with_coord" \
      --run-mask "$MASK" \
      --path-to-case "${case_path}/filtered_wiemip_output"
  fi
done

echo "=== 3. layer geometry sidecars ==="
python build_layer_geometry.py \
  --root "$BASE" \
  --raw-cache "$BASE/raw_cache" \
  --combine-csv processing_combine_list_overshoot.csv \
  --dataset-label "Overshoot WIEMIP output (\`$(basename "$BASE")\`, \`filtered_with_coord\`)." \
  --time-chunk 24 --overwrite

echo "=== 4. rebuild time axis -> filtered_with_coord_fixed ==="
python -W ignore fix_time_and_coords.py "$BASE" \
  --case-input-subdir filtered_with_coord \
  --case-output-subdir filtered_with_coord_fixed \
  --run-mask "$MASK" --overwrite

echo "=== done $(date -Is)  log: $LOG ==="
