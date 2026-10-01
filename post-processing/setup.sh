#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source the configuration (override with WIEMIP_CONFIG=config_overshoot_historic_rerun.sh)
source "$DIR/${WIEMIP_CONFIG:-config.sh}"

if [ "$PROCESS_FROM_LIST" != "true" ]; then
    LOCAL_BASE_RUN="$OUTPUT_DIR/base_run"
    LOCAL_WET_RUN="$OUTPUT_DIR/wet_run"
    LOCAL_WIEMIP_OUTPUT="$OUTPUT_DIR/wiemip_output"
    FIGURES_DIR="$OUTPUT_DIR/figures"

    # Create directories if they do not exist
    mkdir -p "$LOCAL_BASE_RUN" "$LOCAL_WET_RUN" "$LOCAL_WIEMIP_OUTPUT" "$FIGURES_DIR"

    # Copy variables from GCS to local target directories
    for var in "${VAR_NAMES[@]}"; do
        echo "Downloading $var from BASE_RUN to local base_run..."
        # Downloading files containing _tr or similar as matching the pattern. 
        # Usually they look like ALD_yearly_tr.nc or EET_monthly_tr.nc
        gsutil cp "$BASE_RUN/${var}_*tr*.nc" "$LOCAL_BASE_RUN/"
        
        echo "Downloading $var from WET_RUN to local wetland_run..."
        gsutil cp "$WET_RUN/${var}_*tr*.nc" "$LOCAL_WET_RUN/"
    done
    echo "Download complete. Starting Python processing..."
else
    echo "PROCESS_FROM_LIST is true. Skipping global directory creation and download in setup.sh."
    echo "The Python script will handle downloading and directory creation per case."
fi

# Activate the python virtual environment
if [ ! -f "$DIR/venv/bin/activate" ]; then
    echo "Virtual environment not found. Creating one in $DIR/venv..."
    python3 -m venv "$DIR/venv"
    source "$DIR/venv/bin/activate"
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install numpy xarray matplotlib cartopy netCDF4 psutil
else
    echo "Activating existing virtual environment..."
    source "$DIR/venv/bin/activate"
fi

# Execute the data processing Python script
python3 -u process_wiemip.py
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Processing failed with exit code $exit_code"
    exit $exit_code
fi

echo "Processing complete."

# Optional: add run-mask coords + rebuild time on filtered NetCDFs
FIX_FILTERED_TIME_AND_COORDS="${FIX_FILTERED_TIME_AND_COORDS:-false}"
ADD_COORDS_BEFORE_FIX="${ADD_COORDS_BEFORE_FIX:-true}"
RUN_MASK="${RUN_MASK:-$DIR/run-mask2.nc}"
ADD_COORDS_SCRIPT="$DIR/add_coords_from_runmask.py"
FIX_TIME_SCRIPT="$DIR/fix_time_and_coords.py"

if [ "$FIX_FILTERED_TIME_AND_COORDS" = "true" ]; then
    echo ""
    echo "============================================================"
    echo "Fixing time and coordinates on filtered_wiemip_output"
    echo "  RUN_MASK=$RUN_MASK"
    echo "  ADD_COORDS_BEFORE_FIX=$ADD_COORDS_BEFORE_FIX"
    echo "============================================================"

    if [ ! -f "$RUN_MASK" ]; then
        echo "ERROR: run-mask not found: $RUN_MASK"
        exit 1
    fi
    if [ ! -f "$ADD_COORDS_SCRIPT" ] || [ ! -f "$FIX_TIME_SCRIPT" ]; then
        echo "ERROR: missing $ADD_COORDS_SCRIPT or $FIX_TIME_SCRIPT"
        exit 1
    fi

    if [ "$PROCESS_FROM_LIST" = "true" ]; then
        CASE_DIRS=( "$OUTPUT_DIR"/DVM-DOS-TEM_* )
    else
        CASE_DIRS=( "$OUTPUT_DIR" )
    fi

    fixed_any=false
    for CASE_DIR in "${CASE_DIRS[@]}"; do
        [ -d "$CASE_DIR" ] || continue
        FILTERED_DIR="$CASE_DIR/filtered_wiemip_output"
        if [ ! -d "$FILTERED_DIR" ] || ! compgen -G "$FILTERED_DIR"/*.nc > /dev/null; then
            continue
        fi

        CASE_NAME="$(basename "$CASE_DIR")"
        FIX_CASE="${CASE_NAME}_filtered_with_coord"
        FIX_INPUT_ROOT="$OUTPUT_DIR/fix_input"
        FIX_INPUT_DIR="$FIX_INPUT_ROOT/$FIX_CASE"
        FIXED_DIR="$OUTPUT_DIR/ProcessedOutput_fixed/$CASE_NAME"

        echo ""
        echo "--- $CASE_NAME ($FILTERED_DIR) ---"

        if [ "$ADD_COORDS_BEFORE_FIX" = "true" ]; then
            echo "  add_coords_from_runmask.py (in-place)..."
            python3 -u "$ADD_COORDS_SCRIPT" \
                --data-dir "$FILTERED_DIR" \
                --run-mask "$RUN_MASK" \
                --inplace \
                --overwrite-coords
        fi

        echo "  fix_time_and_coords.py..."
        rm -rf "$FIX_INPUT_DIR"
        mkdir -p "$FIX_INPUT_DIR"
        for nc in "$FILTERED_DIR"/*.nc; do
            ln -sf "$nc" "$FIX_INPUT_DIR/$(basename "$nc")"
        done

        python3 -u "$FIX_TIME_SCRIPT" \
            --input-root "$FIX_INPUT_ROOT" \
            --outdir-root "$OUTPUT_DIR" \
            --run-mask "$RUN_MASK" \
            --cases "$FIX_CASE" \
            --overwrite

        if [ ! -d "$FIXED_DIR" ] || ! compgen -G "$FIXED_DIR"/*.nc > /dev/null; then
            echo "ERROR: fix_time_and_coords produced no files in $FIXED_DIR"
            exit 1
        fi

        echo "  copying fixed files back to $FILTERED_DIR ..."
        cp -a "$FIXED_DIR"/*.nc "$FILTERED_DIR/"
        fixed_any=true
    done

    if [ "$fixed_any" = "false" ]; then
        echo "WARNING: FIX_FILTERED_TIME_AND_COORDS=true but no filtered_wiemip_output/*.nc found under $OUTPUT_DIR"
    else
        echo "Time/coordinate fix complete."
    fi
fi
