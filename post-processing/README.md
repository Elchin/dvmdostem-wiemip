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
| `FIX_FILTERED_TIME_AND_COORDS` | `"true"`: after filtering, run coord + time fix on `filtered_wiemip_output` |
| `ADD_COORDS_BEFORE_FIX` | `"true"`: call `add_coords_from_runmask.py` before `fix_time_and_coords.py` |
| `RUN_MASK` | NetCDF with `X`, `Y`, `lat`, `lon` (default: `run-mask2.nc` in this directory) |
| `MERGE_SPATIAL_BBOX` / `FULL_SPATIAL_SHAPE` | For cropped RawOutputRepeat grids (inclusive row/col ends, then embed to full 123×720) |
| `PROCESS_ROW_LIST` | 1-based row indices in the combine list (e.g. `2` = historic, `3` = `l`) |
| `VAR_NAMES`, `AGG_*` | Variables to download/process and map aggregation for figures |

### Batch CSV files

- **`path_gs_merge.csv`** / **`path_gs_merge_overshoot.csv`**: `run_case` → GCS folder with `{VAR}_*.nc`
- **`path_gs_merge_overshoot_rerun.csv`**: alternate GCS paths for overshoot reruns (e.g. RawOutputRepeat historic FireOn)
- **`processing_combine_list_overshoot.csv`**: `WIEMIP_Experiment_Prefix`, `Base_Run`, `Wet_Run`, `Combine`

## 2. What `setup.sh` does

1. Sources `config.sh` (or `WIEMIP_CONFIG`).
2. Activates `venv/` (creates it if missing).
3. Runs **`process_wiemip.py`** (download to shared `raw_cache/`, merge, convert, figures).
4. If `FILTERED=true`, runs **`filter_processed_data_v1.py`** per case → **`filtered_wiemip_output/`**.
5. If `FIX_FILTERED_TIME_AND_COORDS=true`:
   - Optional **`add_coords_from_runmask.py`** (in-place on filtered files)
   - **`fix_time_and_coords.py`** (rebuild time + coords; copies back to `filtered_wiemip_output/`)
   - Also writes **`ProcessedOutput_fixed/<case>/`**

## 3. Overshoot rerun wrappers

| Script | Config | Case (row) |
|--------|--------|------------|
| `./run_historic_overshoot_rerun.sh` | `config_overshoot_historic_rerun.sh` | `DVM-DOS-TEM_historic` (row 2) |
| `./run_overshoot_l_rerun.sh` | `config_overshoot_l_rerun.sh` | `DVM-DOS-TEM_l` (row 3) |

Default output root: `/mnt/disks/wiemip-data/re-run-overshoot`.

Historic rerun uses RawOutputRepeat FireOn (`all_merged_filtered`) with **`MERGE_SPATIAL_BBOX=34,108,0,719`**; `l` uses full-grid RawOutput paths (no bbox).

## 4. Output layout (batch mode)

Under `OUTPUT_DIR/`:

```text
raw_cache/<Base_or_Wet_run_name>/     # shared downloads
DVM-DOS-TEM_<case>/
  wiemip_output/                      # merged WIEMIP NetCDFs
  filtered_wiemip_output/             # range-filtered products
  figures/                            # diagnostic PNGs
ProcessedOutput_fixed/<case>/         # copy after time/coord fix (when enabled)
fix_input/                            # staging for fix_time_and_coords
```

## 5. Coordinate and time utilities

- **`add_coords_from_runmask.py`**: attach `X`, `Y`, `lat`, `lon` from run-mask; does not fix time.
- **`fix_time_and_coords.py`**: rebuild overshoot/1pctCO2 time axes and coords (from [wiemip_scripts](https://github.com/chujin/wiemip_scripts)); can run standalone on a staged case folder under `fix_input/<case>_filtered_with_coord/`.

Example (single case, after filtering):

```bash
python add_coords_from_runmask.py \
  --data-dir /path/to/DVM-DOS-TEM_historic/filtered_wiemip_output \
  --run-mask ./run-mask2.nc --inplace --overwrite-coords

python fix_time_and_coords.py \
  --input-root /path/to/fix_input \
  --outdir-root /path/to/output_root \
  --run-mask ./run-mask2.nc \
  --cases DVM-DOS-TEM_historic_filtered_with_coord --overwrite
```

## 6. Variable processing

**`output_conversion_table.csv`** defines `VarClass` (units, PFT/layer sums, math) and merge flags.

**`output_filters_v1.csv`** drives **`filter_processed_data_v1.py`** value ranges.

## 7. Merging equation

When `Combine` is TRUE, wetland fraction from **`wetland.nc`** (`veg_pct_cov`):

```text
Merged = (Base * veg_frac) + (Wet * (1 - veg_frac))
```

For cropped base grids, set **`MERGE_SPATIAL_BBOX`** and **`FULL_SPATIAL_SHAPE`** so wet/mask slices align and outputs are embedded on the full WIEMIP grid.

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
