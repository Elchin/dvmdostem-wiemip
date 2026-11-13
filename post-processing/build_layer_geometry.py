#!/usr/bin/env python3
"""
Build layer_geometry sidecar NetCDFs (Option A) aligned with filtered_with_coord soilT.

Variables (float32): layer_thickness, layer_bottom_depth, layer_mid_depth (m).
Source: LAYERDZ from WIEMIP base run (same as mrso/mrsoLayer post-processing).
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

import netCDF4 as nc
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
FILL = np.float32(-9999.0)


def resolve_base_run(case_name: str, combine_csv: Path) -> str:
    with open(combine_csv, newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2 or row[0].startswith("WIEMIP"):
                continue
            prefix = row[0].strip()
            base = row[1].strip()
            suffix = row[4].strip() if len(row) >= 5 else ""
            if f"{prefix}{suffix}" == case_name:
                return base
    raise ValueError(f"No combine-list row for case {case_name} in {combine_csv}")


def layerdz_path(raw_cache_dir: Path, base_run: str) -> Path:
    cache = raw_cache_dir / base_run
    hits = sorted(glob.glob(str(cache / "LAYERDZ_*.nc")))
    if not hits:
        raise FileNotFoundError(f"LAYERDZ not in {cache}")
    return Path(hits[0])


def git_postprocessing_rev() -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(SCRIPT_DIR.parent), "log", "-1", "--format=%h %s (%ci)"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return "unknown (not a git checkout)"


def write_readme(
    readme_path: Path,
    *,
    case_name: str,
    base_run: str,
    geometry_file: str,
    dataset_label: str,
    raw_cache_dir: Path,
) -> None:
    rev = git_postprocessing_rev()
    text = f"""# Layer geometry sidecar — `{case_name}`

{dataset_label}

## DVM-DOS-TEM / WIEMIP provenance

- **Model:** DVM-DOS-TEM (DOS-TEM soil column with 22 dynamic layers).
- **WIEMIP post-processing repo:** `dvmdostem-wiemip` at commit/log:  
  `{rev}`
- **Layer thickness source:** raw model output `LAYERDZ` from base run  
  **`{base_run}`** under `{raw_cache_dir}`.
- **Note:** This is the **base (upland) run** thickness, consistent with how
  **`mrso`** / **`mrsoLayer`** are computed. Wetland-merge scenarios blend
  layer **values** (e.g. `soilT`) by layer index but do **not** blend
  `LAYERDZ` from the wetland run.

The resolved column is typically **~5–7 m** (median); thick organic cells can
exceed **~20 m**. This is **not** the full mineral/bedrock column to 55 m
(deeper state lives in separate raw variables such as `TMINEA/B/C`, not in
WIEMIP layer products).

## File

- **`{geometry_file}`** — monthly (`*_mon_05.nc`), same `time`, `layer`, `y`, `x`
  (and `lat`/`lon`) as **`soilT_mon_05.nc`**.

| Variable | Units | Description |
|----------|-------|-------------|
| `layer_thickness` | m | `LAYERDZ` (thickness of each model layer) |
| `layer_bottom_depth` | m | depth to bottom of layer from surface (cumulative sum) |
| `layer_mid_depth` | m | centre of layer = bottom − thickness/2 |

`layer` index **0** = surface; **21** = deepest resolved layer.

## Using with `soilT`, `mrsoLayer`, `cSoilLayers`

### `soilT` (monthly, K)

Open both NetCDFs and match on `(time, layer, y, x)`:

```python
import xarray as xr

soil = xr.open_dataset("..._soilT_mon_05.nc")
geo = xr.open_dataset("..._layer_geometry_mon_05.nc")

yi, xi = 50, 400
prof = soil.soilT.isel(y=yi, x=xi)
z = geo.layer_mid_depth.isel(y=yi, x=xi)

# depth increases downward (invert y-axis when plotting)
```

### `mrsoLayer` (monthly, kg m⁻²)

Same **layer index** and **monthly** `time` as `soilT`. Column integral
**`mrso`** used base-run `LAYERDZ` when converting VWC → kg m⁻².

### `cSoilLayers` (annual, kg C m⁻²)

Annual file uses the same **22 layer indices** but a **yearly** time axis.
Use this **monthly** geometry for **layer index** `k`; for a given year, pick
representative depths (e.g. `layer_mid_depth.sel(time=slice('1870','1870'))`
or mean over months in that year).

## Fill values

Masked/off-land cells use `_FillValue` **{FILL}** (aligned with WIEMIP products).

## Contact

Woodwell WIEMIP / DVM-DOS-TEM post-processing (`dvmdostem-wiemip/post-processing`).
"""
    readme_path.write_text(text, encoding="utf-8")


COORD_NAMES = frozenset({"time", "X", "Y", "lat", "lon", "x", "y"})


def copy_coord_vars(nc_in: nc.Dataset, nc_out: nc.Dataset, t_len: int) -> None:
    for name, v_in in nc_in.variables.items():
        if name not in COORD_NAMES or name in nc_out.variables:
            continue
        if v_in.dimensions == ("time",) and len(v_in) >= t_len:
            v_out = nc_out.createVariable(name, v_in.datatype, v_in.dimensions)
            v_out.setncatts({k: v_in.getncattr(k) for k in v_in.ncattrs()})
            v_out[:] = v_in[:t_len]
        elif "time" not in v_in.dimensions:
            v_out = nc_out.createVariable(name, v_in.datatype, v_in.dimensions)
            v_out.setncatts({k: v_in.getncattr(k) for k in v_in.ncattrs()})
            v_out[:] = v_in[:]


def build_one(
    case_dir: Path,
    raw_cache_dir: Path,
    combine_csv: Path,
    dataset_label: str,
    overwrite: bool,
    time_chunk: int = 24,
) -> None:
    case_name = case_dir.name
    out_dir = case_dir / "filtered_with_coord"
    if not out_dir.is_dir():
        raise FileNotFoundError(f"Missing {out_dir}")

    template = out_dir / f"{case_name}_soilT_mon_05.nc"
    if not template.is_file():
        raise FileNotFoundError(f"Missing template {template}")

    out_nc = out_dir / f"{case_name}_layer_geometry_mon_05.nc"
    readme = out_dir / "LAYER_GEOMETRY_README.md"
    if out_nc.exists() and not overwrite:
        print(f"  skip (exists): {out_nc}")
        if not readme.exists():
            base_run = resolve_base_run(case_name, combine_csv)
            write_readme(
                readme,
                case_name=case_name,
                base_run=base_run,
                geometry_file=out_nc.name,
                dataset_label=dataset_label,
                raw_cache_dir=raw_cache_dir,
            )
        return

    base_run = resolve_base_run(case_name, combine_csv)
    ldz_path = layerdz_path(raw_cache_dir, base_run)
    print(f"  {case_name}: LAYERDZ <- {base_run} ({ldz_path.name})")

    with nc.Dataset(template, "r") as nc_tmpl:
        if "soilT" not in nc_tmpl.variables:
            raise ValueError(f"soilT missing in {template}")
        v_soil = nc_tmpl.variables["soilT"]
        soil_fill = getattr(v_soil, "_FillValue", FILL)
        dim_time = len(nc_tmpl.dimensions["time"]) if "time" in nc_tmpl.dimensions else v_soil.shape[0]
        dim_names = v_soil.dimensions
        layer_len = len(nc_tmpl.dimensions["layer"])
        ny, nx = v_soil.shape[-2], v_soil.shape[-1]

    with nc.Dataset(ldz_path, "r") as nc_ldz:
        v_ldz = nc_ldz.variables["LAYERDZ"]
        if v_ldz.shape[0] < dim_time:
            dim_time = v_ldz.shape[0]
            print(f"    trimming time to {dim_time} (LAYERDZ length)")

    if out_nc.exists():
        out_nc.unlink()

    with nc.Dataset(template, "r") as nc_tmpl, nc.Dataset(out_nc, "w", format="NETCDF4") as nc_out:
        for dname, dim in nc_tmpl.dimensions.items():
            length = dim_time if dname == "time" and not dim.isunlimited() else (len(dim) if not dim.isunlimited() else None)
            nc_out.createDimension(dname, length)
        copy_coord_vars(nc_tmpl, nc_out, dim_time)

        out_dims = dim_names
        chunking = (min(time_chunk, dim_time), layer_len, ny, nx)

        attrs_common = {
            "units": "m",
            "source_LAYERDZ_run": base_run,
            "comment": "From base-run LAYERDZ; see LAYER_GEOMETRY_README.md",
        }
        vars_out = {}
        for vname, long_name in (
            ("layer_thickness", "Layer thickness (LAYERDZ)"),
            ("layer_bottom_depth", "Depth to layer bottom from surface"),
            ("layer_mid_depth", "Layer mid-point depth from surface"),
        ):
            v = nc_out.createVariable(
                vname,
                np.float32,
                out_dims,
                zlib=True,
                chunksizes=chunking,
                fill_value=FILL,
            )
            v.long_name = long_name
            for k, val in attrs_common.items():
                setattr(v, k, val)
            vars_out[vname] = v

        nc_out.title = f"{case_name} layer geometry (sidecar for soilT/mrsoLayer)"
        nc_out.history = f"build_layer_geometry.py; {git_postprocessing_rev()}"

        with nc.Dataset(ldz_path, "r") as nc_ldz, nc.Dataset(template, "r") as nc_soil:
            v_ldz = nc_ldz.variables["LAYERDZ"]
            v_soil = nc_soil.variables["soilT"]
            for t0 in range(0, dim_time, time_chunk):
                t1 = min(t0 + time_chunk, dim_time)
                dz = np.asarray(v_ldz[t0:t1, ...], dtype=np.float32)
                dz = np.where(dz == -9999, FILL, dz)
                dz = np.where(np.isfinite(dz), dz, FILL)

                soil_t = np.asarray(v_soil[t0:t1, ...], dtype=np.float32)
                missing = (soil_t == soil_fill) | ~np.isfinite(soil_t)
                dz = np.where(missing, FILL, dz)

                bottom = np.cumsum(dz, axis=1).astype(np.float32)
                mid = (bottom - dz / 2.0).astype(np.float32)
                bottom = np.where(missing, FILL, bottom)
                mid = np.where(missing, FILL, mid)

                vars_out["layer_thickness"][t0:t1, ...] = np.ascontiguousarray(dz)
                vars_out["layer_bottom_depth"][t0:t1, ...] = np.ascontiguousarray(bottom)
                vars_out["layer_mid_depth"][t0:t1, ...] = np.ascontiguousarray(mid)
                nc_out.sync()
                print(f"    time {t0}:{t1} / {dim_time}")

    write_readme(
        readme,
        case_name=case_name,
        base_run=base_run,
        geometry_file=out_nc.name,
        dataset_label=dataset_label,
        raw_cache_dir=raw_cache_dir,
    )
    print(f"  wrote {out_nc}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True, help="Parent dir with DVM-DOS-TEM_* case folders")
    p.add_argument("--raw-cache", type=Path, required=True)
    p.add_argument(
        "--combine-csv",
        type=Path,
        default=SCRIPT_DIR / "processing_combine_list.csv",
    )
    p.add_argument("--dataset-label", default="WIEMIP processed output (filtered_with_coord).")
    p.add_argument("--cases", nargs="*", default=None, help="Case folder names; default all DVM-DOS-TEM_*")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--time-chunk", type=int, default=24)
    args = p.parse_args()

    if args.cases:
        case_dirs = [args.root / c for c in args.cases]
    else:
        case_dirs = sorted(args.root.glob("DVM-DOS-TEM_*"))

    failures = 0
    for case_dir in case_dirs:
        if not case_dir.is_dir():
            print(f"skip missing {case_dir}")
            failures += 1
            continue
        try:
            build_one(
                case_dir,
                args.raw_cache,
                args.combine_csv,
                args.dataset_label,
                args.overwrite,
                args.time_chunk,
            )
        except Exception as exc:
            failures += 1
            print(f"ERROR {case_dir.name}: {exc}", file=sys.stderr)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()