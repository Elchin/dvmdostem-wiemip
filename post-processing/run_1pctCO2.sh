#!/bin/bash
# Full 1pctCO2 post-processing: merge/convert/filter -> coords -> COU noFire t=0
# adjust -> layer geometry -> time/coord fix -> deltaC figure.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
export WIEMIP_CONFIG=config_1pctCO2.sh
source "$DIR/$WIEMIP_CONFIG"
BASE="$OUTPUT_DIR"
MASK="$DIR/run-mask2.nc"

mkdir -p "$BASE"
LOG="$BASE/run_1pctCO2_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
echo "=== 1pctCO2 post-processing $(date -Is)  OUTPUT_DIR=$BASE ==="

if ! compgen -G "$DIR/$MERGE_MASK_DIR/merge_mask_*.nc" > /dev/null; then
  echo "ERROR: no wetland merge masks in $DIR/$MERGE_MASK_DIR (see README: build_wetland_merge_masks.py)"
  exit 1
fi

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

echo "=== 3. COU noFire land-C t=0 adjust ==="
python adjust_cou_landc_t0.py --base "$BASE"

echo "=== 4. layer geometry sidecars ==="
python build_layer_geometry.py \
  --root "$BASE" \
  --raw-cache "$BASE/raw_cache" \
  --combine-csv processing_combine_list.csv \
  --dataset-label "1pctCO2 WIEMIP output (\`$(basename "$BASE")\`, \`filtered_with_coord\`)." \
  --time-chunk 24 --overwrite

echo "=== 5. rebuild time axis -> filtered_with_coord_fixed ==="
python -W ignore fix_time_and_coords.py "$BASE" \
  --case-input-subdir filtered_with_coord \
  --case-output-subdir filtered_with_coord_fixed \
  --run-mask "$MASK" --overwrite

echo "=== 6. deltaC QA figure ==="
python "$DIR/../analysis/plot_deltaC_1pctCO2.py" \
  --base "$BASE" \
  --source filtered_with_coord \
  --match_cou_coverage \
  --out-dir "$BASE/figures"

echo "=== done $(date -Is)  log: $LOG ==="
