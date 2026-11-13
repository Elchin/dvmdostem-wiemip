#!/bin/bash
# 1pctCO2 post-processing (cases in processing_combine_list.csv, GCS paths in
# path_gs_merge.csv). Wetland blend is gated by masks in MERGE_MASK_DIR. Used by run_1pctCO2.sh.
# PROCESS_ROW_LIST: 1-based rows of the combine list, e.g. "1,6"; empty = all 25 cases.
# Raw downloads go to $OUTPUT_DIR/raw_cache.

export OUTPUT_DIR="/mnt/disks/wiemip-data/1pctCO2_processed_matchmerge"
export MERGE_MASK_DIR="wetland_merge_masks"
export GCM_PATTERN="bgc"
export EXPERIMENT="FireOn"
export PROCESS="noProcess"
export PROCESS_FROM_LIST="true"
export OVERSHOOT="false"
export FILTERED="true"
export PROCESS_ROWS="all"
export PROCESS_ROW_LIST=""
export SKIP_DOWNLOAD_IF_EXISTS="true"
export MAX_WORKERS="4"

VAR_NAMES=(ALD AVLN BURNSOIL2AIRC BURNVEG2AIRC CH4EFFLUXTOT DWDC EET GPP LAI LFNVC LFVC NETNMIN NPP NUPTAKELAB NUPTAKEST ORGN RHSOM SNOWTHICK SOC SOC0_100cm SWE TRANSPIRATION VEGC VEGNTOT TLAYER VWCLAYER WATERTAB)

export AGG_ALD="mean"
export AGG_AVLN="mean"
export AGG_BURNSOIL2AIRC="sum"
export AGG_BURNVEG2AIRC="sum"
export AGG_CH4EFFLUXTOT="sum"
export AGG_DWDC="mean"
export AGG_EET="sum"
export AGG_GPP="sum"
export AGG_LAI="mean"
export AGG_LFNVC="sum"
export AGG_LFVC="sum"
export AGG_NETNMIN="sum"
export AGG_NPP="sum"
export AGG_NUPTAKELAB="sum"
export AGG_NUPTAKEST="sum"
export AGG_ORGN="mean"
export AGG_QRUNOFF="sum"
export AGG_RHSOM="sum"
export AGG_SNOWTHICK="mean"
export AGG_SOC="mean"
export AGG_SOC0_100cm="mean"
export AGG_SWE="mean"
export AGG_TLAYER="mean"
export AGG_TRANSPIRATION="sum"
export AGG_VEGC="mean"
export AGG_VEGNTOT="mean"
export AGG_VWCLAYER="mean"
export AGG_WATERTAB="mean"
