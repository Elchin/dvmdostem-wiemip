# WIEMIP Post-Processing (1pctCO2 and overshoot)

Converts raw DVM-DOS-TEM output on GCS into WIEMIP NetCDF products: download,
base/wetland merge, unit conversion, range filtering, coordinates, layer
geometry and a rebuilt time axis.

## Quick start

```bash
cd /mnt/disks/wiemip-data/dvmdostem-wiemip/post-processing

nohup ./run_1pctCO2.sh   > /dev/null 2>&1 &   # 25 cases -> /mnt/disks/wiemip-data/1pctCO2_processed_matchmerge
nohup ./run_overshoot.sh > /dev/null 2>&1 &   # 6 cases  -> /mnt/disks/wiemip-data/re-run-overshoot
```

Each driver writes a timestamped log to its output root
(`run_1pctCO2_<date>.log`, `run_overshoot_<date>.log`). A full run takes many
hours and needs several hundred GB of free disk per experiment.

Requirements: authenticated `gsutil`, and the Python venv in `venv/`
(`setup.sh` creates it on first run with `numpy xarray matplotlib cartopy netCDF4 psutil`).

## Pipeline

Both drivers run the same steps; 1pctCO2 has two extra ones.

| Step | Script | Output (per case) |
|------|--------|-------------------|
| 1. Download, merge, convert, figures | `setup.sh` → `process_wiemip.py` | `wiemip_output/`, `figures/` |
| 2. Range filter (called by step 1) | `filter_processed_data_v1.py` | `filtered_wiemip_output/` |
| 3. Add `X`, `Y`, `lat`, `lon` from `run-mask2.nc` | `process_all_cases_add_coords.py` → `add_coords_from_runmask.py` | `filtered_with_coord/` |
| 4. *(1pctCO2 only)* COU `noFire` land-C t=0 alignment | `adjust_cou_landc_t0.py` | edits `filtered_with_coord/` in place |
| 5. Soil layer geometry sidecar | `build_layer_geometry.py` | `filtered_with_coord/{case}_layer_geometry_mon_05.nc`, `LAYER_GEOMETRY_README.md` |
| 6. Rebuild time axis, re-stamp coords | `fix_time_and_coords.py` | `filtered_with_coord_fixed/` (**final product**) |
| 7. *(1pctCO2 only)* ΔC QA figure | `../analysis/plot_deltaC_1pctCO2.py` | `<output root>/figures/` |

### Step details

- **Raw cache.** Each unique base/wetland run is downloaded once into
  `<output root>/raw_cache/<run name>/` (`VAR_NAMES` from the config plus
  `LAYERDZ`). With `SKIP_DOWNLOAD_IF_EXISTS="true"` existing files are reused.
- **Merge.** When `Combine` is `TRUE` in the combine list:
  `Merged = Base * veg_frac + Wet * (1 - veg_frac)`, with `veg_frac` from
  `wetland.nc` (`veg_pct_cov`). Base and wetland runs must share the full
  123 × 720 grid. For 1pctCO2 the blend is further restricted to cells in the
  masks under `wetland_merge_masks/` (see below).
- **Variables.** `output_conversion_table.csv` maps raw DVM-DOS-TEM variables to
  WIEMIP names, units, PFT/layer sums and derived ("math") variables.
  `output_filters_v1.csv` holds the valid value range per variable.
- **COU noFire alignment (1pctCO2).** For `DVM-DOS-TEM_*_cou_noFire`, `cVeg`,
  `cSoil` and `cCwd` are shifted per cell so that at t=0 they equal the paired
  `stable_ctrl_*` case; a `README.md` documenting this is written into each
  adjusted folder.
- **Time axis.** The earlier steps leave `time` as NaN after the first step.
  `fix_time_and_coords.py` rebuilds it from the series length, as
  `days since 1850-01-01`, calendar `365_day`:

  | Experiment | Yearly length | Monthly length | Start |
  |------------|---------------|----------------|-------|
  | 1pctCO2 | 150 (or 151) | 1800 (or 1812) | 1850 |
  | overshoot `ctrl`, `historic` | 174 | 2088 | 1850 |
  | overshoot `l`, `m`, `hl`, `hl_cf` | 277 | 3324 | 2024 |

  This copy of the script (from [chujin/wiemip_coords](https://github.com/chujin/wiemip_coords))
  is patched to keep each variable's source compression and chunking; the
  upstream version writes uncompressed files that are ~10× larger.

## Configuration

| File | Purpose |
|------|---------|
| `config_1pctCO2.sh` | 1pctCO2 settings: `OUTPUT_DIR`, `VAR_NAMES`, `MAX_WORKERS=4`, `MERGE_MASK_DIR` |
| `config_overshoot.sh` | Overshoot settings: `OUTPUT_DIR`, `VAR_NAMES`, `MAX_WORKERS=1`, `PATH_GS_MERGE_CSV` |
| `processing_combine_list.csv` | 1pctCO2 cases: `WIEMIP_Experiment_Prefix, Base_Run, Wet_Run, Combine, noProcess` suffix |
| `processing_combine_list_overshoot.csv` | Overshoot cases (`ctrl`, `historic`, `l`, `hl`, `hl_cf`, `m`) |
| `path_gs_merge.csv` | 1pctCO2 run name → GCS folder |
| `path_gs_merge_overshoot_rerun.csv` | Overshoot run name → GCS folder (FireOn from `RawOutputRepeat`, wetland from `RawOutput/.../all_merged_restored`) |
| `run-mask2.nc` | Grid coordinates (`X`, `Y`, `lat`, `lon`), 123 × 720 |
| `wetland.nc` | Wetland fraction used for the merge |
| `wetland_merge_masks/` | 1pctCO2 wetland-blend masks |

**Processing a subset of cases.** Set `PROCESS_ROW_LIST` in the config to
1-based data rows of the combine list (e.g. `"1,3"` for overshoot `ctrl` and
`l`); leave it empty for all cases. `process_wiemip.py` reads this from the
config file, not from the environment. Steps 3–6 of the drivers loop over all
case folders in the output root.

**Running only step 1.** `WIEMIP_CONFIG=config_1pctCO2.sh ./setup.sh` (or
`config_overshoot.sh`). `setup.sh` refuses to run without `WIEMIP_CONFIG`.

**Rebuilding the 1pctCO2 wetland merge masks.** Only needed if the raw
wetland runs change. The masks are built from the raw cache, so download first:

```bash
WIEMIP_CONFIG=config_1pctCO2.sh ./setup.sh          # fills raw_cache
venv/bin/python build_wetland_merge_masks.py \
  --raw-cache /mnt/disks/wiemip-data/1pctCO2_processed_matchmerge/raw_cache \
  --out-dir wetland_merge_masks
./run_1pctCO2.sh                                    # reuses raw_cache
```

`build_wetland_merge_masks.py` imports `../analysis/plot_deltaCL_from_merged_cl.py`.

## Output layout

```text
<output root>/
  raw_cache/<run name>/*.nc            shared raw downloads
  DVM-DOS-TEM_<case>/
    wiemip_output/                     merged WIEMIP NetCDFs
    filtered_wiemip_output/            range-filtered
    filtered_with_coord/               + X, Y, lat, lon (+ layer geometry)
    filtered_with_coord_fixed/         + rebuilt time axis  <- deliverable
    figures/                           diagnostic maps
```

File names follow `<case>_<wiemip var>_<yr|mon>_05.nc`, e.g.
`DVM-DOS-TEM_ctrl_gpp_mon_05.nc`.

## Analysis / QA plots

```bash
# Overshoot domain-mean time series for all variables
../analysis/run_overshoot_new.sh       # env: DATA_ROOT, INPUT_SUBDIR, SCENARIOS, OUTDIR, STITCH

# One variable
venv/bin/python ../analysis/plot_overshoot_new.py \
  --var gpp --freq mon --agg mean \
  --data-root /mnt/disks/wiemip-data/re-run-overshoot \
  --input-subdir filtered_with_coord_fixed \
  --scenarios historic l \
  --outdir /mnt/disks/wiemip-data/re-run-overshoot/figures

# 1pctCO2 land-carbon change (run automatically by run_1pctCO2.sh)
venv/bin/python ../analysis/plot_deltaC_1pctCO2.py \
  --base /mnt/disks/wiemip-data/1pctCO2_processed_matchmerge \
  --source filtered_with_coord --match_cou_coverage \
  --out-dir /mnt/disks/wiemip-data/1pctCO2_processed_matchmerge/figures
```
