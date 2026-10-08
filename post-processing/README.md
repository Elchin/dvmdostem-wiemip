# WIEMIP Post-Processing Pipeline

This directory contains the automated pipeline for downloading, merging, converting, filtering, and plotting DVM-DOS-TEM output for WIEMIP.

## 1. Configuration and entry point

Edit **`config.sh`** (or a case-specific config such as **`config_overshoot_historic_rerun.sh`**) and run:

```bash
cd post-processing
time ./setup.sh
```

Use an alternate config without editing the default file:

```bash
export WIEMIP_CONFIG=config_overshoot_historic_rerun.sh
time ./setup.sh
```

### Main `config.sh` options

| Variable | Purpose |
|----------|---------|
| `PROCESS_FROM_LIST` | `"true"`: batch mode from CSV lists; `"false"`: single `BASE_RUN` / `WET_RUN` |
| `OVERSHOOT` | `"true"`: use `path_gs_merge_overshoot.csv` and `processing_combine_list_overshoot.csv` |
| `PATH_GS_MERGE_CSV` | Optional override (e.g. `path_gs_merge_overshoot_rerun.csv`) |
| `OUTPUT_DIR` | Root for `raw_cache/`, per-case outputs, and figures |
| `FILTERED` | `"true"`: run `filter_processed_data_v1.py` after each case |
| `PROCESS_ROW_LIST` | 1-based row indices in the combine list (e.g. `2` = historic, `3` = `l`) |
| `VAR_NAMES`, `AGG_*` | Variables to download/process and map aggregation for figures |

### Batch CSV files

- **`path_gs_merge.csv`** / **`path_gs_merge_overshoot.csv`**: `run_case` → GCS folder with `{VAR}_*.nc`
- **`path_gs_merge_overshoot_rerun.csv`**: alternate GCS paths; historic/l FireOn align with full-grid `Merged1` / `RawOutputRepeat` `Merged5` (same lineage as `path_gs_merge_overshoot.csv`) for a continuous historic→Future_l boundary
- **`processing_combine_list_overshoot.csv`**: `WIEMIP_Experiment_Prefix`, `Base_Run`, `Wet_Run`, `Combine`

## 2. What `setup.sh` does

1. Sources `config.sh` (or `WIEMIP_CONFIG`).
2. Activates `venv/` (creates it if missing).
3. Runs **`process_wiemip.py`** (download to shared `raw_cache/`, merge, convert, figures).
4. If `FILTERED=true`, runs **`filter_processed_data_v1.py`** per case → **`filtered_wiemip_output/`**.

## 3. Overshoot rerun wrappers

| Script | Config | Case (row) |
|--------|--------|------------|
| `./run_historic_overshoot_rerun.sh` | `config_overshoot_historic_rerun.sh` | `DVM-DOS-TEM_historic` (row 2) |
| `./run_overshoot_l_rerun.sh` | `config_overshoot_l_rerun.sh` | `DVM-DOS-TEM_l` (row 3) |

Default output root: `/mnt/disks/wiemip-data/re-run-overshoot`.

## 4. Output layout (batch mode)

Under `OUTPUT_DIR/`:

```text
raw_cache/<Base_or_Wet_run_name>/     # shared downloads
DVM-DOS-TEM_<case>/
  wiemip_output/                      # merged WIEMIP NetCDFs
  filtered_wiemip_output/             # range-filtered products
  figures/                            # diagnostic PNGs
```

## 5. Optional coordinate utilities (manual)

Standalone scripts (not run by `setup.sh`):

- **`add_coords_from_runmask.py`**: attach `X`, `Y`, `lat`, `lon` from run-mask.
- **`fix_time_and_coords.py`**: rebuild overshoot/1pctCO2 time axes and coords (from [wiemip_scripts](https://github.com/chujin/wiemip_scripts)).

See each script’s `--help` or docstring for usage.

## 6. Variable processing

**`output_conversion_table.csv`** defines `VarClass` (units, PFT/layer sums, math) and merge flags.

**`output_filters_v1.csv`** drives **`filter_processed_data_v1.py`** value ranges.

## 7. Merging equation

When `Combine` is TRUE, wetland fraction from **`wetland.nc`** (`veg_pct_cov`):

```text
Merged = (Base * veg_frac) + (Wet * (1 - veg_frac))
```

Base and wetland runs must use the same full spatial grid (123×720).

## 8. Memory and 4D variables

`process_wiemip.py` streams large 4D fields in native time chunks (~120 steps) via `netCDF4` to limit RAM. See inline handling for `TLAYER`, `VWCLAYER`, `RHSOM`, etc.

## 9. Analysis plots

Repository **`analysis/plot_overshoot_new.py`** plots domain-mean timeseries from filtered products:

```bash
../post-processing/venv/bin/python ../analysis/plot_overshoot_new.py \
  --var gpp --freq mon --agg mean \
  --data-root /mnt/disks/wiemip-data/re-run-overshoot \
  --input-subdir filtered \
  --scenarios historic l \
  --outdir /mnt/disks/wiemip-data/re-run-overshoot/analysis_figures
```

Use subfolder **`filtered`** or **`filtered_wiemip_output`** (script tries both).
