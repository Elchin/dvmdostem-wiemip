#!/bin/bash
cd /mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing
source venv/bin/activate

for case in DVM-DOS-TEM_ctrl DVM-DOS-TEM_historic DVM-DOS-TEM_hl DVM-DOS-TEM_hl_cf DVM-DOS-TEM_l DVM-DOS-TEM_m; do
  echo "=========================================================="
  echo "Processing $case..."
  echo "=========================================================="
  
  # Only run if the filtered_wiemip_output directory exists
  if [ -d "/mnt/disks/wiemip-data/newly_processed/${case}/filtered_wiemip_output" ]; then
    python process_all_cases_add_coords.py \
      --work-root "/mnt/disks/wiemip-data/newly_processed/${case}/filtered_with_coord" \
      --run-mask "/mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing/run-mask2.nc" \
      --path-to-case "/mnt/disks/wiemip-data/newly_processed/${case}/filtered_wiemip_output"
  else
    echo "Directory /mnt/disks/wiemip-data/newly_processed/${case}/filtered_wiemip_output does not exist. Skipping."
  fi
done
