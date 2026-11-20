#!/bin/bash
# Analyze PF-AK v0.1 dataset using bash/awk

PFAK_FILE="${1:-PF_AK_v0.1_b4e8.csv}"

echo "=========================================="
echo "PF-AK v0.1 Dataset Analysis"
echo "=========================================="
echo "File: ${PFAK_FILE}"
echo ""

# Check file exists
if [ ! -f "${PFAK_FILE}" ]; then
    echo "Error: File not found: ${PFAK_FILE}"
    exit 1
fi

# Header
echo "Dataset Structure:"
echo "------------------"
head -1 "${PFAK_FILE}"
echo ""

# Total rows
TOTAL_ROWS=$(wc -l < "${PFAK_FILE}")
echo "Total rows: $((TOTAL_ROWS - 1)) (excluding header)"
echo ""

# Stations
echo "=========================================="
echo "Station Summary"
echo "=========================================="
echo ""
echo "Total unique stations:"
awk -F',' 'NR>1 {print $1}' "${PFAK_FILE}" | sort -u | wc -l
echo ""

echo "Station list with coordinates:"
awk -F',' 'NR>1 {print $1,$3,$4}' "${PFAK_FILE}" | sort -u | head -20
echo ""
echo "(showing first 20 of 72 stations)"
echo ""

# Prototype stations
echo "=========================================="
echo "Prototype Station Analysis"
echo "=========================================="

analyze_station() {
    local STATION=$1
    echo ""
    echo "--------------------"
    echo "Station: ${STATION}"
    echo "--------------------"
    
    # Get station info
    STATION_INFO=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st {print $2,$3,$4; exit}' "${PFAK_FILE}")
    if [ -z "${STATION_INFO}" ]; then
        echo "  ✗ Station not found in dataset"
        return
    fi
    
    CODE=$(echo $STATION_INFO | cut -d' ' -f1)
    LAT=$(echo $STATION_INFO | cut -d' ' -f2)
    LON=$(echo $STATION_INFO | cut -d' ' -f3)
    
    echo "  Code: ${CODE}"
    echo "  Location: ${LAT}°N, ${LON}°W"
    
    # Count records
    TOTAL=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st' "${PFAK_FILE}" | wc -l)
    echo "  Total months: ${TOTAL}"
    
    # Year range
    YEARS=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st {print $5}' "${PFAK_FILE}" | sort -u)
    FIRST_YEAR=$(echo "$YEARS" | head -1)
    LAST_YEAR=$(echo "$YEARS" | tail -1)
    echo "  Years: ${FIRST_YEAR}-${LAST_YEAR}"
    
    # Variable availability
    echo ""
    echo "  Variable availability:"
    
    # Tair
    TAIR_COUNT=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st && $8!=-999.99' "${PFAK_FILE}" | wc -l)
    PCT=$(awk "BEGIN {printf \"%.1f\", ($TAIR_COUNT / $TOTAL * 100)}")
    echo "    Tair (Air temp):    ${TAIR_COUNT}/${TOTAL} (${PCT}%)"
    
    # Snod
    SNOD_COUNT=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st && $7!=-999.99' "${PFAK_FILE}" | wc -l)
    PCT=$(awk "BEGIN {printf \"%.1f\", ($SNOD_COUNT / $TOTAL * 100)}")
    echo "    Snod (Snow depth):  ${SNOD_COUNT}/${TOTAL} (${PCT}%)"
    
    # Ts25cm
    TS25_COUNT=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st && $10!=-999.99' "${PFAK_FILE}" | wc -l)
    PCT=$(awk "BEGIN {printf \"%.1f\", ($TS25_COUNT / $TOTAL * 100)}")
    echo "    Ts25cm (Ground):    ${TS25_COUNT}/${TOTAL} (${PCT}%)"
    
    # Ts50cm
    TS50_COUNT=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st && $11!=-999.99' "${PFAK_FILE}" | wc -l)
    PCT=$(awk "BEGIN {printf \"%.1f\", ($TS50_COUNT / $TOTAL * 100)}")
    echo "    Ts50cm (Ground):    ${TS50_COUNT}/${TOTAL} (${PCT}%)"
    
    # Ts75cm
    TS75_COUNT=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st && $12!=-999.99' "${PFAK_FILE}" | wc -l)
    PCT=$(awk "BEGIN {printf \"%.1f\", ($TS75_COUNT / $TOTAL * 100)}")
    echo "    Ts75cm (Ground):    ${TS75_COUNT}/${TOTAL} (${PCT}%)"
    
    # Ts100cm
    TS100_COUNT=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st && $9!=-999.99' "${PFAK_FILE}" | wc -l)
    PCT=$(awk "BEGIN {printf \"%.1f\", ($TS100_COUNT / $TOTAL * 100)}")
    echo "    Ts100cm (Ground):   ${TS100_COUNT}/${TOTAL} (${PCT}%)"
    
    # VWC
    VWC_COUNT=$(awk -F',' -v st="\"${STATION}\"" 'NR>1 && $1==st && $14!=-999.99' "${PFAK_FILE}" | wc -l)
    PCT=$(awk "BEGIN {printf \"%.1f\", ($VWC_COUNT / $TOTAL * 100)}")
    echo "    VWC_top (Soil moist): ${VWC_COUNT}/${TOTAL} (${PCT}%)"
}

# Analyze prototype stations
analyze_station "Deadhorse"
analyze_station "Imnaviat"
analyze_station "Smith Lake 1"

echo ""
echo "=========================================="
echo "Analysis Complete"
echo "=========================================="
echo ""
echo "Prototype stations identified:"
echo "  1. Deadhorse (North Slope tundra, continuous permafrost)"
echo "  2. Imnaviat (Arctic foothills, near Toolik coordinates)"
echo "  3. Smith Lake 1 (Interior Alaska, boreal forest)"
echo ""
