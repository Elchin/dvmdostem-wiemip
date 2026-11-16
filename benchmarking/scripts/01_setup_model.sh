#!/bin/bash
# Script to clone and build DVM-DOS-TEM model for benchmarking
# Uses wetland/reburn-switch branch with enthalpy thermal method

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BENCHMARK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODEL_DIR="${BENCHMARK_ROOT}/model/dvm-dos-tem"

echo "=========================================="
echo "DVM-DOS-TEM Model Setup"
echo "=========================================="
echo "Benchmark root: ${BENCHMARK_ROOT}"
echo "Model directory: ${MODEL_DIR}"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# Check if model already exists
if [ -d "${MODEL_DIR}" ]; then
    print_warning "Model directory already exists: ${MODEL_DIR}"
    echo "  Use this directory or remove it to clone fresh"
    
    # Check if it's the right repository
    cd "${MODEL_DIR}"
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    
    if [[ "${REMOTE_URL}" == *"Elchin/dvm-dos-tem"* ]]; then
        print_status "Correct repository found"
        
        # Check branch
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        echo "  Current branch: ${CURRENT_BRANCH}"
        
        if [ "${CURRENT_BRANCH}" != "wetland/reburn-switch" ]; then
            print_warning "Not on wetland/reburn-switch branch"
            echo "  Switch with: cd ${MODEL_DIR} && git checkout wetland/reburn-switch"
        else
            print_status "On correct branch: wetland/reburn-switch"
        fi
        
        # Pull latest changes
        echo ""
        read -p "Pull latest changes from remote? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git pull origin wetland/reburn-switch
            print_status "Repository updated"
        fi
    else
        print_error "Wrong repository found (not Elchin/dvm-dos-tem)"
        echo "  Please remove ${MODEL_DIR} and run this script again"
        exit 1
    fi
else
    # Clone the repository
    echo "Cloning DVM-DOS-TEM repository..."
    echo "  URL: https://github.com/Elchin/dvm-dos-tem"
    echo "  Branch: wetland/reburn-switch"
    echo ""
    
    mkdir -p "${BENCHMARK_ROOT}/model"
    cd "${BENCHMARK_ROOT}/model"
    
    git clone --branch wetland/reburn-switch \
        https://github.com/Elchin/dvm-dos-tem.git \
        dvm-dos-tem
    
    print_status "Repository cloned successfully"
    
    cd "${MODEL_DIR}"
    git log -1 --oneline
fi

echo ""
echo "=========================================="
echo "Checking Dependencies"
echo "=========================================="
echo ""

# Check for required build tools
check_command() {
    if command -v $1 &> /dev/null; then
        print_status "$1 found"
        return 0
    else
        print_error "$1 not found"
        return 1
    fi
}

MISSING_DEPS=0

# C++ compiler
if command -v g++ &> /dev/null; then
    print_status "g++ found ($(g++ --version | head -1))"
elif command -v clang++ &> /dev/null; then
    print_status "clang++ found ($(clang++ --version | head -1))"
else
    print_error "No C++ compiler found (g++ or clang++)"
    MISSING_DEPS=1
fi

# CMake
check_command cmake || MISSING_DEPS=1

# Make
check_command make || MISSING_DEPS=1

# NetCDF
if command -v nc-config &> /dev/null; then
    print_status "NetCDF found ($(nc-config --version))"
else
    print_warning "nc-config not found (NetCDF may not be installed)"
    echo "  Install with: apt-get install libnetcdf-dev (Ubuntu/Debian)"
    echo "            or: brew install netcdf (macOS)"
    MISSING_DEPS=1
fi

# Boost
if [ -d /usr/include/boost ] || [ -d /usr/local/include/boost ]; then
    print_status "Boost headers found"
else
    print_warning "Boost headers not found at standard locations"
    echo "  Install with: apt-get install libboost-all-dev (Ubuntu/Debian)"
    echo "            or: brew install boost (macOS)"
    MISSING_DEPS=1
fi

# jsoncpp
if pkg-config --exists jsoncpp; then
    print_status "jsoncpp found ($(pkg-config --modversion jsoncpp))"
else
    print_warning "jsoncpp not found"
    echo "  Install with: apt-get install libjsoncpp-dev (Ubuntu/Debian)"
    echo "            or: brew install jsoncpp (macOS)"
    MISSING_DEPS=1
fi

echo ""

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Some dependencies are missing"
    echo ""
    echo "Install all dependencies on Ubuntu/Debian:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y build-essential cmake libnetcdf-dev \\"
    echo "                          libboost-all-dev libjsoncpp-dev \\"
    echo "                          libreadline-dev git"
    echo ""
    echo "Install all dependencies on macOS:"
    echo "  brew install cmake netcdf boost jsoncpp readline"
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "=========================================="
echo "Building DVM-DOS-TEM"
echo "=========================================="
echo ""

cd "${MODEL_DIR}"

# Create build directory
if [ -d build ]; then
    print_warning "Build directory exists, cleaning..."
    rm -rf build
fi

mkdir build
cd build

echo "Running CMake..."
cmake ..

if [ $? -eq 0 ]; then
    print_status "CMake configuration successful"
else
    print_error "CMake configuration failed"
    exit 1
fi

echo ""
echo "Building (this may take several minutes)..."
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)

if [ $? -eq 0 ]; then
    print_status "Build successful"
    
    # Check for executable
    if [ -f dvmdostem ]; then
        print_status "dvmdostem executable created"
        echo "  Location: ${MODEL_DIR}/build/dvmdostem"
        
        # Test run
        echo ""
        echo "Testing executable..."
        ./dvmdostem --help > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            print_status "Executable runs successfully"
        else
            print_warning "Executable may have issues (check dependencies)"
        fi
    else
        print_error "dvmdostem executable not found after build"
        exit 1
    fi
else
    print_error "Build failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Model Setup Complete"
echo "=========================================="
echo ""
print_status "DVM-DOS-TEM ready for benchmarking"
echo "  Model: ${MODEL_DIR}"
echo "  Executable: ${MODEL_DIR}/build/dvmdostem"
echo "  Branch: wetland/reburn-switch"
echo ""
echo "Next steps:"
echo "  1. Complete data acquisition (download PF-AK and ERA5)"
echo "  2. Prepare input files for prototype stations"
echo "  3. Run model for prototype stations"
echo ""
