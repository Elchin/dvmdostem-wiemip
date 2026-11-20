#!/bin/bash
# Master script for Phase 1 data acquisition
# Downloads all necessary data for prototype station benchmarking

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BENCHMARK_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=========================================="
echo "Phase 1 Data Acquisition"
echo "=========================================="
echo "Benchmark root: ${BENCHMARK_ROOT}"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Step 1: Download PF-AK dataset
echo "=========================================="
echo "Step 1: PF-AK v0.1 Dataset"
echo "=========================================="
echo ""
echo "The PF-AK dataset must be downloaded manually from Arctic Data Center."
echo "Running download script to generate instructions..."
echo ""

cd "${SCRIPT_DIR}"
python3 download_pfak.py --dest-dir "${BENCHMARK_ROOT}/data/observations/synthesis"

print_warning "Manual download required for PF-AK dataset"
echo "  See: ${BENCHMARK_ROOT}/data/observations/synthesis/DOWNLOAD_INSTRUCTIONS.txt"
echo ""

# Step 2: Check for CDS API setup
echo "=========================================="
echo "Step 2: ERA5 Data (via CDS API)"
echo "=========================================="
echo ""

if [ ! -f ~/.cdsapirc ]; then
    print_warning "CDS API not configured"
    echo ""
    echo "To download ERA5 data automatically, you need to:"
    echo "  1. Register at https://cds.climate.copernicus.eu/"
    echo "  2. Get API key from https://cds.climate.copernicus.eu/api-how-to"
    echo "  3. Create ~/.cdsapirc with:"
    echo "     url: https://cds.climate.copernicus.eu/api/v2"
    echo "     key: YOUR_UID:YOUR_API_KEY"
    echo "  4. Install cdsapi: pip install cdsapi"
    echo ""
    print_warning "Skipping ERA5 download (CDS API not configured)"
    echo ""
else
    print_status "CDS API configuration found"
    
    # Check if cdsapi is installed
    if ! python3 -c "import cdsapi" 2>/dev/null; then
        print_warning "cdsapi Python package not installed"
        echo "  Install with: pip install cdsapi"
        echo ""
    else
        print_status "cdsapi Python package installed"
        
        # Download ERA5 for prototype stations
        echo ""
        echo "Downloading ERA5 data for prototype stations..."
        echo "  Stations: Deadhorse, Toolik"
        echo "  Period: 1997-2016"
        echo "  This may take 10-30 minutes depending on CDS queue..."
        echo ""
        
        python3 download_era5.py \
            --dest-dir "${BENCHMARK_ROOT}/data/climate/ERA5" \
            --stations Deadhorse Toolik \
            --start-year 1997 \
            --end-year 2016
        
        if [ $? -eq 0 ]; then
            print_status "ERA5 download completed"
        else
            print_error "ERA5 download failed"
            echo "  Check CDS API credentials and service status"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "Data Acquisition Summary"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Complete manual PF-AK download (see instructions above)"
echo "  2. Verify ERA5 data downloaded successfully"
echo "  3. Clone and build DVM-DOS-TEM model"
echo "  4. Prepare model input files"
echo ""
echo "For detailed workflow, see:"
echo "  ${BENCHMARK_ROOT}/metadata/README.md"
echo "  ${BENCHMARK_ROOT}/../docs/ground-temperature-benchmarking-plan.md"
echo ""
