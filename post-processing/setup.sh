#!/bin/bash

# Source the configuration
source ~/dvmdostem-wiemip/post-processing/config.sh

# Target directories expected by the postprocessing script
export OUTPUT_DIR="/mnt/disks/wiemip-data/output"
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

# Activate the python virtual environment
source ~/venv/bin/activate

# Execute the data processing Python script
python3 -u process_wiemip.py

echo "Processing complete."
