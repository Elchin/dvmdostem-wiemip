#!/bin/bash

# Activate virtual environment
source /mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing/venv/bin/activate

# Loop through all DVM-DOS-TEM_* directories
for dir in /mnt/disks/wiemip-data/processed/DVM-DOS-TEM_*; do
    if [ -d "$dir" ]; then
        # Check if filtered_v1 directory already exists
        if [ ! -d "$dir/filtered_v1" ]; then
            echo "Processing $dir..."
            python /mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing/filter_processed_data_v1.py "$dir"
            echo "Finished $dir"
            echo "----------------------------------------"
        else
            echo "Skipping $dir - filtered_v1 already exists"
        fi
    fi
done

echo "All missing cases have been processed."
