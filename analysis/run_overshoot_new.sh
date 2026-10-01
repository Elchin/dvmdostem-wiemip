#!/bin/bash

source /mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing/venv/bin/activate

OUTDIR="/mnt/disks/wiemip-data/dvmdostem-wiemip/analysis/overshoot_new_figs"
mkdir -p "$OUTDIR"

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
    var=$(echo $item | awk '{print $1}')
    freq=$(echo $item | awk '{print $2}')
    
    echo "Running analysis for $var ($freq)..."
    python /mnt/disks/wiemip-data/dvmdostem-wiemip/analysis/plot_overshoot_new.py --var "$var" --freq "$freq" --outdir "$OUTDIR"
done
