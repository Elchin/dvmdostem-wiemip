#!/bin/bash

# Define the Google Cloud Storage URIs for the two simulations
WET_RUN="gs://wiemip/SimulationOuput/RawOutput/bgc/Special_bgc_WetlandOn_split/all_merged"
BASE_RUN="gs://wiemip/SimulationOuput/RawOutput/bgc/Special_bgc_FireOn/Special_bgc_FireOn_1_Merged1"

# Meta parameters for naming convention
export GCM_PATTERN="bgc"
export EXPERIMENT="FireOn"
export PROCESS="noProcess"

# The variables to process and copy
VAR_NAMES=(ALD AVLN BURNSOIL2AIRC BURNVEG2AIRC CH4EFFLUXTOT DWDC EET GPP LAI LFNVC LFVC NETNMIN NPP NUPTAKELAB NUPTAKEST ORGN RHSOM SNOWTHICK SOC SOC0_100cm SWE TLAYER TRANSPIRATION VEGC VEGNTOT VWCLAYER WATERTAB cSoil gpp npp ra cSoilBelow1m fVegSoil fNup)

# Time aggregation settings
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
#<MODEL_NAME>_<gcm_pattern_short_name>_<experiment_short_name>_<variable_name>_<frequency>_noProcess_<spatial_resolution_short_name>.nc
