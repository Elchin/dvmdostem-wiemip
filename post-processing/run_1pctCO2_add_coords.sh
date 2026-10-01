#!/bin/bash
cd /mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing
source venv/bin/activate

# Define the base directory
BASE_DIR="/mnt/disks/wiemip-data/1pctCO2_processed"

# Loop through all DVM-DOS-TEM_* folders in the 1pctCO2_processed directory
for case_path in ${BASE_DIR}/DVM-DOS-TEM_*; do
  # Extract just the case name (e.g., DVM-DOS-TEM_gfdl_cou)
  case=$(basename "$case_path")
  
  echo "=========================================================="
  echo "Processing $case..."
  echo "=========================================================="
  
  # Only run if the filtered_wiemip_output directory exists
  if [ -d "${BASE_DIR}/${case}/filtered_wiemip_output" ]; then
    python process_all_cases_add_coords.py \
      --work-root "${BASE_DIR}/${case}/filtered_with_coord" \
      --run-mask "/mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing/run-mask2.nc" \
      --path-to-case "${BASE_DIR}/${case}/filtered_wiemip_output"
  else
    echo "Directory ${BASE_DIR}/${case}/filtered_wiemip_output does not exist. Skipping."
  fi
done
