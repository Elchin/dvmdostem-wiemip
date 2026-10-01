# DVM-DOS-TEM WIEMIP Setup Scripts

This repository contains setup scripts for fetching and structuring input files for the WIEMIP simulations with DVM-DOS-TEM.

## Setup Scripts

There are two primary setup scripts, depending on the type of simulation you are running:
1. `setup_1pctCO2_sim_files.py` - For 1% CO2 simulations.
2. `setup_overshoot_sim_files.py` - For overshoot simulations.

Both scripts read from their respective CSV manifest files to determine which Google Cloud Storage (`gs://`) objects to download and where to place them for the model to use.

### Usage

The basic usage is the same for both scripts. You can run them with Python 3:

```bash
python3 setup_1pctCO2_sim_files.py --simulation <SIMULATION_NAME> --dest-folder <DESTINATION_DIRECTORY>
```

```bash
python3 setup_overshoot_sim_files.py --simulation <SIMULATION_NAME> --dest-folder <DESTINATION_DIRECTORY>
```

#### Arguments:

- `--simulation`: **(Required/Inferred)** The target simulation case to create. The script will create a sub-directory with this exact name inside the destination folder.
  - *Note:* You can also pass the simulation name directly as a flag, e.g., `--Special_spin_WetlandOn`, which the script will automatically recognize.
- `--dest-folder`: **(Optional)** The base destination directory where the simulation folder will be created. 
  - Defaults to `/mnt/exacloud/$USER` (e.g. `/mnt/exacloud/ejafarov_woodwellclimate_org`).

### Output Structure

When run, the script will create a new directory for the specified simulation inside the destination folder. It will construct standard DVM-DOS-TEM input structures:

```text
<DESTINATION_DIRECTORY>/<SIMULATION_NAME>/
├── config/
│   ├── config.js
│   └── output_spec.csv
├── input/
│   ├── run-mask.nc
│   ├── historic-climate.nc
│   └── ... (other simulation-specific input files)
└── ReadMe_.txt
```

- For the **1% CO2** simulations (`setup_1pctCO2_sim_files.py`), if a constant simulation is detected, the script will automatically generate a `ch4.nc` file from the `co2.nc` template and overwrite constant CO2 values with the proper constant CH4 value (1015.0).
- The `ReadMe_.txt` generated in each simulation folder will document the execution date and exactly which files were copied from GCS.

### Dependencies
- Python 3
- `gsutil` / `gcloud storage cp` CLI configured and authenticated.
- The `netCDF4` python module (required for generating constant `ch4.nc` in `setup_1pctCO2_sim_files.py`).

## Post-processing and analysis

After simulations finish, raw DVM-DOS-TEM output on GCS is converted to WIEMIP NetCDF products under `post-processing/`. See **[post-processing/README.md](post-processing/README.md)** for:

- Batch merge/conversion (`setup.sh`, `process_wiemip.py`)
- Overshoot reruns (`path_gs_merge_overshoot_rerun.csv`, `run_historic_overshoot_rerun.sh`, `run_overshoot_l_rerun.sh`)
- Range filtering, time/coordinate fixes on filtered files
- Optional coord utilities (`add_coords_from_runmask.py`, `fix_time_and_coords.py`)

Quick start (default `config.sh`):

```bash
cd post-processing
time ./setup.sh
```

Overshoot historic rerun example:

```bash
cd post-processing
./run_historic_overshoot_rerun.sh
```

Timeseries comparison plots for processed cases live in **`analysis/`** (e.g. `plot_overshoot_new.py`).
