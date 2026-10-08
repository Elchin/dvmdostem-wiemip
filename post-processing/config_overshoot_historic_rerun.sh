#!/bin/bash
# Historic overshoot: full-grid RawOutput FireOn + Wetland merge (see path_gs_merge_overshoot_rerun.csv).
# Use with: WIEMIP_CONFIG=config_overshoot_historic_rerun.sh ./run_historic_overshoot_rerun.sh

WET_RUN="gs://wiemip/OvershootOutput/RawOutput/historic/Special_historic_Wetland_split/all_merged_restored"
BASE_RUN="gs://wiemip/OvershootOutput/RawOutput/historic/Special_historic_FireOn_1_Merged1"

export OUTPUT_DIR="/mnt/disks/wiemip-data/re-run-overshoot"
export GCM_PATTERN="historical"
export EXPERIMENT="FireOn"
export PROCESS="noProcess"
export PROCESS_FROM_LIST="true"
export OVERSHOOT="true"
export PATH_GS_MERGE_CSV="path_gs_merge_overshoot_rerun.csv"
export FILTERED="true"
export PROCESS_ROWS="all"
export PROCESS_ROW_LIST="2,3"
export SKIP_DOWNLOAD_IF_EXISTS="true"
export MAX_WORKERS="1"

VAR_NAMES=(SOC)
    
#ALD AVLN BURNSOIL2AIRC BURNVEG2AIRC CH4EFFLUXTOT DWDC EET GPP LAI LFNVC LFVC NETNMIN NPP NUPTAKELAB NUPTAKEST ORGN RHSOM SNOWTHICK SOC SOC0_100cm SWE TLAYER TRANSPIRATION VEGC VEGNTOT VWCLAYER WATERTAB cSoil gpp npp ra cSoilBelow1m fVegSoil fNup)

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
