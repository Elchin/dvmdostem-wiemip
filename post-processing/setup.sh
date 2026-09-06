#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source the configuration
source "$DIR/config.sh"

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

echo "Processing complete."
