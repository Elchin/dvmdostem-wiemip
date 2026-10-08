#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WIEMIP_CONFIG="${WIEMIP_CONFIG:-config_overshoot_l_rerun.sh}"
source "$DIR/$WIEMIP_CONFIG"

CASE="DVM-DOS-TEM_l"
CASE_DIR="$OUTPUT_DIR/$CASE"
FILTERED_DIR="$CASE_DIR/filtered_wiemip_output"
LOG="$OUTPUT_DIR/run_overshoot_l_rerun.log"

mkdir -p "$OUTPUT_DIR" /mnt/disks/wiemip-data/tmp
exec > >(tee -a "$LOG") 2>&1

echo "============================================================"
echo "Special_l overshoot rerun started $(date -Iseconds)"
echo "  OUTPUT_DIR=$OUTPUT_DIR"
echo "  PATH_GS_MERGE_CSV=$PATH_GS_MERGE_CSV"
echo "  PROCESS_ROW_LIST=$PROCESS_ROW_LIST (DVM-DOS-TEM_l)"
echo "============================================================"

if [[ "${CLEAR_L_CACHE:-1}" == "1" ]]; then
  rm -rf "$OUTPUT_DIR/raw_cache/Special_l_FireOn" "$OUTPUT_DIR/raw_cache/Special_l_Wetland"
fi

cd "$DIR"
time ./setup.sh

if [[ ! -d "$FILTERED_DIR" ]] || ! compgen -G "$FILTERED_DIR"/*.nc > /dev/null; then
  echo "ERROR: Expected NetCDF files in $FILTERED_DIR"
  exit 1
fi

echo ""
echo "============================================================"
echo "Done $(date -Iseconds)"
echo "  filtered_wiemip_output: $FILTERED_DIR"
echo "  log:                    $LOG"
echo "============================================================"
