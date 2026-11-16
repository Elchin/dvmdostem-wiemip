#!/bin/bash
# Master script for Phase 1 data acquisition with CRU baseline
# Updated configuration: CRU-TS baseline + station observation substitution

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BENCHMARK_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=========================================="
echo "Phase 1 Data Acquisition (CRU Baseline)"
echo "=========================================="
echo "Configuration: CRU-TS 1900-2024 + Station Observations"
echo "Benchmark root: ${BENCHMARK_ROOT}"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Configuration summary
echo "=========================================="
echo "Updated Configuration"
echo "=========================================="
echo "Run parameters:"
echo "  PR (Pre-run):   100 years"
echo "  EQ (Equilibrium): 2000 years"
echo "  SP (Spin-up):   200 years"
echo "  TR (Transient): 124 years (1900-2024)"
echo ""
echo "Climate data strategy:"
echo "  • CRU-TS as baseline (1901-2022/2024)"
echo "  • Station observations substituted where available"
echo "  • Variables: temperature, precipitation, vapor pressure, cloud cover"
echo ""
echo "Validation period:"
echo "  • 1901-1997: Climate trends (no ground temp observations)"
echo "  • 1997-2016: Full validation (PF-AK observations)"
echo "  • 2017-2024: Extended period (if station data available)"
echo ""

# Step 1: CRU-TS Download
echo "=========================================="
echo "Step 1: CRU-TS Dataset"
echo "=========================================="
echo ""
print_info "CRU-TS (CRU Time Series) v4.07"
echo "  Source: Climatic Research Unit, University of East Anglia"
echo "  Resolution: 0.5° × 0.5°"
echo "  Period: 1901-2022"
echo "  Variables: temperature, precipitation, vapor pressure, cloud cover"
echo ""

CRU_DIR="${BENCHMARK_ROOT}/data/climate/CRU"
mkdir -p "${CRU_DIR}"

# Check if CRU files already downloaded
CRU_DOWNLOADED=false
if [ -f "${CRU_DIR}/cru_ts4.07.1901.2022.tmp.dat.nc" ]; then
    print_status "CRU temperature file found"
    CRU_DOWNLOADED=true
else
    print_warning "CRU files not yet downloaded"
fi

if [ "$CRU_DOWNLOADED" = false ]; then
    echo ""
    print_info "CRU files must be downloaded manually (large files: ~200-600 MB each)"
    echo ""
    echo "Download options:"
    echo ""
    echo "Option 1: CRU Website (direct download)"
    echo "  URL: https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/"
    echo ""
    echo "Option 2: CEDA Archive (requires free registration)"
    echo "  URL: https://data.ceda.ac.uk/badc/cru/data/cru_ts/cru_ts_4.07/data/"
    echo ""
    echo "Option 3: wget (command line)"
    echo "  cd ${CRU_DIR}"
    echo "  wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/tmp/cru_ts4.07.1901.2022.tmp.dat.nc.gz"
    echo "  wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/pre/cru_ts4.07.1901.2022.pre.dat.nc.gz"
    echo "  wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/vap/cru_ts4.07.1901.2022.vap.dat.nc.gz"
    echo "  wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/cld/cru_ts4.07.1901.2022.cld.dat.nc.gz"
    echo "  gunzip *.gz"
    echo ""
    echo "Required files:"
    echo "  1. cru_ts4.07.1901.2022.tmp.dat.nc (mean temperature)"
    echo "  2. cru_ts4.07.1901.2022.pre.dat.nc (precipitation)"
    echo "  3. cru_ts4.07.1901.2022.vap.dat.nc (vapor pressure)"
    echo "  4. cru_ts4.07.1901.2022.cld.dat.nc (cloud cover)"
    echo ""
    echo "Place files in: ${CRU_DIR}"
    echo ""
    
    # Create instructions file
    cat > "${CRU_DIR}/DOWNLOAD_INSTRUCTIONS.txt" << 'EOF'
CRU-TS Data Download Instructions
================================================================================

Download CRU-TS v4.07 files from:
https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/

Required files (download and decompress):

1. Temperature (tmp):
   https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/tmp/cru_ts4.07.1901.2022.tmp.dat.nc.gz
   → cru_ts4.07.1901.2022.tmp.dat.nc

2. Precipitation (pre):
   https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/pre/cru_ts4.07.1901.2022.pre.dat.nc.gz
   → cru_ts4.07.1901.2022.pre.dat.nc

3. Vapor Pressure (vap):
   https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/vap/cru_ts4.07.1901.2022.vap.dat.nc.gz
   → cru_ts4.07.1901.2022.vap.dat.nc

4. Cloud Cover (cld):
   https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/cld/cru_ts4.07.1901.2022.cld.dat.nc.gz
   → cru_ts4.07.1901.2022.cld.dat.nc

Quick download (bash):
--------------------------------------------------------------------------------
cd [THIS_DIRECTORY]

wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/tmp/cru_ts4.07.1901.2022.tmp.dat.nc.gz
wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/pre/cru_ts4.07.1901.2022.pre.dat.nc.gz
wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/vap/cru_ts4.07.1901.2022.vap.dat.nc.gz
wget https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07/cld/cru_ts4.07.1901.2022.cld.dat.nc.gz

gunzip *.gz

After download, run:
python3 ../scripts/download_data/download_cru.py --cru-dir .

Citation:
--------------------------------------------------------------------------------
Harris, I., Osborn, T.J., Jones, P. et al. (2020). Version 4 of the CRU TS
monthly high-resolution gridded multivariate climate dataset. Sci Data 7, 109.
https://doi.org/10.1038/s41597-020-0453-3
EOF
    
    print_status "Instructions saved to: ${CRU_DIR}/DOWNLOAD_INSTRUCTIONS.txt"
    
    print_warning "Proceed with manual CRU download, then rerun this script"
else
    print_status "CRU files already downloaded"
    
    # Extract station data from CRU
    echo ""
    print_info "Extracting station data from CRU grids..."
    cd "${SCRIPT_DIR}"
    
    python3 download_cru.py \
        --cru-dir "${CRU_DIR}" \
        --dest-dir "${CRU_DIR}" \
        --stations Deadhorse Toolik \
        --variables tmp pre vap cld
    
    if [ $? -eq 0 ]; then
        print_status "CRU station extraction complete"
    else
        print_error "CRU station extraction failed"
    fi
fi

echo ""

# Step 2: PF-AK Dataset
echo "=========================================="
echo "Step 2: PF-AK v0.1 Dataset"
echo "=========================================="
echo ""

cd "${SCRIPT_DIR}"
python3 download_pfak.py --dest-dir "${BENCHMARK_ROOT}/data/observations/synthesis"

print_warning "Manual download required for PF-AK dataset"
echo "  See: ${BENCHMARK_ROOT}/data/observations/synthesis/DOWNLOAD_INSTRUCTIONS.txt"
echo ""

# Summary
echo "=========================================="
echo "Data Acquisition Summary"
echo "=========================================="
echo ""
echo "Status:"
if [ "$CRU_DOWNLOADED" = true ]; then
    print_status "CRU-TS: Downloaded and extracted"
else
    print_warning "CRU-TS: Manual download required"
fi
print_warning "PF-AK: Manual download required"
echo ""
echo "Next steps:"
echo "  1. Complete CRU download if not done (see instructions above)"
echo "  2. Complete PF-AK download from Arctic Data Center"
echo "  3. Run: python3 download_cru.py --cru-dir ${CRU_DIR} (if not done)"
echo "  4. Verify all data downloaded:"
echo "     - CRU files in ${CRU_DIR}/"
echo "     - PF-AK files in ${BENCHMARK_ROOT}/data/observations/synthesis/"
echo "  5. Proceed with input preparation (merge CRU + station data)"
echo ""
echo "For detailed workflow, see:"
echo "  ${BENCHMARK_ROOT}/PHASE1_WORKFLOW.md"
echo "  /cursor/stores/bc-01a1e1cb-682f-7b77-b8a1-482a5f674d77/internal/phase1-configuration-update.md"
echo ""
