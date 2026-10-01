#!/usr/bin/env python3
"""
Fix boss-provided ProcessedOutput NetCDFs (memory-efficient netCDF4 I/O):

  (1) Rebuild the time coordinate (currently missing / NaN / wrong).
      Overshoot-style:
      - length 174 / 174*12 → yearly/monthly from 1850
      - length 277 / 277*12 → yearly/monthly from 2024
      1pctCO2-style:
      - length 150 / 150*12 → yearly/monthly from 1850
      - length 151 / 151*12 → yearly/monthly from 1850 (rare +1 step)
      Time stored as days since 1850-01-01, calendar 365_day
      (Jan-1 of each year, or 1st of each month).

  (2) Replace X, Y, lat, lon with values from run-mask2.nc.

Outputs (same filenames) under:
  <outdir-root>/ProcessedOutput_fixed/<case>/

  where <case> is the input folder name with trailing
  _filtered_with_coord removed (e.g. DVM-DOS-TEM_gfdl_cou).

Example
-------
  python fix_time_and_coords.py \\
    --input-root  /mnt/exacloud/$USER/wiemip/check_time_coordinate/ProcessedOutput \\
    --outdir-root /mnt/exacloud/$USER/wiemip/check_time_coordinate \\
    --run-mask    /mnt/exacloud/$USER/wiemip/inputs/teminputs/new/run-mask2.nc
"""

from __future__ import annotations

import argparse
import gc
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import netCDF4 as nc
import numpy as np


TIME_UNITS = "days since 1850-01-01"
TIME_CALENDAR = "365_day"
REF_YEAR = 1850

MONTH_LENGTHS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=int)
MONTH_START_DOY = np.concatenate([[0], np.cumsum(MONTH_LENGTHS)[:-1]])

TIME_RULES: Dict[int, Tuple[str, int]] = {
    # overshoot
    174: ("yearly", 1850),
    277: ("yearly", 2024),
    174 * 12: ("monthly", 1850),
    277 * 12: ("monthly", 2024),
    # 1pctCO2
    150: ("yearly", 1850),
    151: ("yearly", 1850),  # occasional +1 year
    150 * 12: ("monthly", 1850),
    151 * 12: ("monthly", 1850),
}

COORD_NAMES = ("X", "Y", "lat", "lon")


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input-root", type=Path, default=here / "ProcessedOutput")
    p.add_argument("--outdir-root", type=Path, default=here)
    p.add_argument(
        "--run-mask",
        type=Path,
        default=Path("/mnt/exacloud/cchang_woodwellclimate_org/wiemip/inputs/teminputs/new/run-mask2.nc"),
    )
    p.add_argument("--cases", nargs="*", default=None)
    p.add_argument("--one-file", default=None, help=argparse.SUPPRESS)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def days_since_1850_yearly(n: int, start_year: int) -> np.ndarray:
    years = np.arange(start_year, start_year + n, dtype=np.int64)
    return ((years - REF_YEAR) * 365).astype(np.float64)


def days_since_1850_monthly(n_months: int, start_year: int) -> np.ndarray:
    out = np.empty(n_months, dtype=np.float64)
    y, m = start_year, 0
    for i in range(n_months):
        out[i] = (y - REF_YEAR) * 365 + MONTH_START_DOY[m]
        m += 1
        if m == 12:
            m = 0
            y += 1
    return out


def build_time_values(n: int) -> Tuple[np.ndarray, str, int]:
    if n not in TIME_RULES:
        raise ValueError(
            f"Unrecognized time length {n}. Expected one of {sorted(TIME_RULES)}."
        )
    freq, start_year = TIME_RULES[n]
    if freq == "yearly":
        values = days_since_1850_yearly(n, start_year)
    else:
        values = days_since_1850_monthly(n, start_year)
    return values, freq, start_year


def load_runmask_coords(path: Path) -> Dict[str, np.ndarray]:
    """Return float32 arrays: Y(ny), X(nx), lat(ny,nx), lon(ny,nx)."""
    with nc.Dataset(path) as ds:
        for v in COORD_NAMES:
            if v not in ds.variables:
                raise SystemExit(f"run-mask missing '{v}': {path}")
        Y = np.asarray(ds.variables["Y"][:], dtype=np.float32)
        X = np.asarray(ds.variables["X"][:], dtype=np.float32)
        lat = np.asarray(ds.variables["lat"][:], dtype=np.float32)
        lon = np.asarray(ds.variables["lon"][:], dtype=np.float32)
        attrs = {v: {a: ds.variables[v].getncattr(a) for a in ds.variables[v].ncattrs()
                     if a != "_FillValue"} for v in COORD_NAMES}

    if Y.ndim != 1 or X.ndim != 1:
        raise SystemExit(f"Expected 1-D Y/X, got Y{Y.shape} X{X.shape}")
    if lat.shape == (X.size, Y.size) and lon.shape == (X.size, Y.size):
        lat = lat.T
        lon = lon.T
    if lat.shape != (Y.size, X.size) or lon.shape != (Y.size, X.size):
        raise SystemExit(
            f"lat/lon shape {lat.shape}/{lon.shape} incompatible with Y={Y.size}, X={X.size}"
        )
    return {"Y": Y, "X": X, "lat": lat, "lon": lon, "_attrs": attrs}


def _copy_ncattrs(src_var, dst_var, skip=("_FillValue",)):
    for a in src_var.ncattrs():
        if a in skip:
            continue
        try:
            dst_var.setncattr(a, src_var.getncattr(a))
        except Exception:
            pass


def _spatial_dim_names(src: nc.Dataset) -> Tuple[str, str]:
    dims = list(src.dimensions.keys())
    if "y" in dims and "x" in dims:
        return "y", "x"
    if "Y" in dims and "X" in dims:
        return "Y", "X"
    # last two dims of first non-coord data var
    for name, var in src.variables.items():
        if name in COORD_NAMES or name == "time":
            continue
        if len(var.dimensions) >= 2:
            return var.dimensions[-2], var.dimensions[-1]
    raise SystemExit(f"Cannot infer spatial dims from {dims}")


def fix_one_file(
    src_path: Path,
    dst_path: Path,
    mask: Dict[str, np.ndarray],
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict:
    report: dict = {"file": src_path.name, "status": "ok"}

    if dst_path.exists() and not overwrite and not dry_run:
        report["status"] = "skip_exists"
        report["out"] = str(dst_path)
        return report

    with nc.Dataset(src_path, "r") as src:
        if "time" not in src.dimensions:
            report["status"] = "error_no_time_dim"
            return report

        n_time = len(src.dimensions["time"])
        report["n_time"] = n_time
        try:
            tvals, freq, start_year = build_time_values(n_time)
        except ValueError as e:
            report["status"] = "error_bad_time_length"
            report["error"] = str(e)
            return report

        y_dim, x_dim = _spatial_dim_names(src)
        ny = len(src.dimensions[y_dim])
        nx = len(src.dimensions[x_dim])
        if ny != mask["Y"].size or nx != mask["X"].size:
            report["status"] = "error_spatial_shape"
            report["error"] = f"file ({ny},{nx}) vs run-mask ({mask['Y'].size},{mask['X'].size})"
            return report

        end_year = start_year + n_time - 1 if freq == "yearly" else start_year + n_time // 12 - 1
        report["time_freq"] = freq
        report["start_year"] = start_year
        report["time_end_year"] = end_year
        report["out"] = str(dst_path)

        if dry_run:
            report["status"] = "dry_run"
            return report

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file then replace (safer if killed mid-write)
        tmp_path = dst_path.with_suffix(dst_path.suffix + ".tmp")
        if tmp_path.exists():
            tmp_path.unlink()

        with nc.Dataset(tmp_path, "w", format="NETCDF4") as dst:
            # Dimensions: keep original names except force spatial to y/x
            for dname, dim in src.dimensions.items():
                if dname == y_dim:
                    dst.createDimension("y", ny)
                elif dname == x_dim:
                    dst.createDimension("x", nx)
                elif dname == "time":
                    dst.createDimension("time", None if dim.isunlimited() else n_time)
                else:
                    dst.createDimension(dname, len(dim) if not dim.isunlimited() else None)

            def map_dims(dims: Tuple[str, ...]) -> Tuple[str, ...]:
                out = []
                for d in dims:
                    if d == y_dim:
                        out.append("y")
                    elif d == x_dim:
                        out.append("x")
                    else:
                        out.append(d)
                return tuple(out)

            # time
            tvar = dst.createVariable("time", "f8", ("time",), fill_value=False)
            tvar[:] = tvals
            tvar.setncattr("units", TIME_UNITS)
            tvar.setncattr("calendar", TIME_CALENDAR)
            tvar.setncattr("long_name", "time")
            tvar.setncattr("standard_name", "time")
            tvar.setncattr("axis", "T")
            tvar.setncattr(
                "comment",
                f"Rebuilt: {freq} series starting {start_year}, n={n_time}, "
                f"days since 1850-01-01 (365_day).",
            )

            # spatial coords from run-mask
            attrs = mask["_attrs"]
            yv = dst.createVariable("Y", "f4", ("y",), fill_value=False)
            yv[:] = mask["Y"]
            for k, v in (attrs.get("Y") or {
                "standard_name": "degree_north",
                "long_name": "y coordinate of projection",
                "units": "degree",
            }).items():
                yv.setncattr(k, v)

            xv = dst.createVariable("X", "f4", ("x",), fill_value=False)
            xv[:] = mask["X"]
            for k, v in (attrs.get("X") or {
                "standard_name": "degree_east",
                "long_name": "x coordinate of projection",
                "units": "degree",
            }).items():
                xv.setncattr(k, v)

            latv = dst.createVariable("lat", "f4", ("y", "x"), fill_value=False)
            latv[:] = mask["lat"]
            for k, v in (attrs.get("lat") or {
                "standard_name": "latitude", "units": "degree_north"
            }).items():
                latv.setncattr(k, v)

            lonv = dst.createVariable("lon", "f4", ("y", "x"), fill_value=False)
            lonv[:] = mask["lon"]
            for k, v in (attrs.get("lon") or {
                "standard_name": "longitude", "units": "degree_east"
            }).items():
                lonv.setncattr(k, v)

            # Copy data variables (skip old time/coords)
            skip = set(COORD_NAMES) | {"time"}
            for name, svar in src.variables.items():
                if name in skip:
                    continue
                dims = map_dims(svar.dimensions)
                dtype = svar.dtype
                fill = None
                if hasattr(svar, "_FillValue"):
                    fill = svar._FillValue
                elif "_FillValue" in svar.ncattrs():
                    fill = svar.getncattr("_FillValue")

                kwargs = {}
                if fill is not None:
                    kwargs["fill_value"] = fill

                # Always slab along time for multi-D fields to avoid HDF/segfaults
                # on large (time, pft, y, x) arrays.
                use_slabs = "time" in dims and svar.ndim >= 3
                if use_slabs:
                    t_axis = dims.index("time")
                    # smaller slabs for 4-D+ (e.g. pft)
                    slab = 1 if svar.ndim >= 4 else 6
                    dvar = dst.createVariable(name, dtype, dims, zlib=False, **kwargs)
                    for t0 in range(0, n_time, slab):
                        t1 = min(t0 + slab, n_time)
                        slicer = [slice(None)] * svar.ndim
                        slicer[t_axis] = slice(t0, t1)
                        slicer = tuple(slicer)
                        dvar[slicer] = np.array(svar[slicer], copy=True)
                        if t0 % 120 == 0:
                            gc.collect()
                else:
                    dvar = dst.createVariable(name, dtype, dims, zlib=False, **kwargs)
                    dvar[:] = np.array(svar[:], copy=True)

                _copy_ncattrs(svar, dvar)
                gc.collect()

            # global attrs
            for a in src.ncattrs():
                try:
                    dst.setncattr(a, src.getncattr(a))
                except Exception:
                    pass
            dst.setncattr("fixed_by", "fix_time_and_coords.py")
            dst.setncattr(
                "fixed_time",
                f"{freq} from {start_year}, length={n_time}, "
                f"units='{TIME_UNITS}', calendar='{TIME_CALENDAR}'",
            )
            dst.setncattr(
                "fixed_coords_from",
                "/mnt/exacloud/cchang_woodwellclimate_org/wiemip/inputs/teminputs/new/run-mask2.nc",
            )

        tmp_path.replace(dst_path)

    gc.collect()
    return report


def list_case_dirs(input_root: Path, cases: Optional[List[str]]) -> List[Path]:
    if cases:
        dirs = [input_root / c for c in cases]
        missing = [d for d in dirs if not d.is_dir()]
        if missing:
            raise SystemExit(f"Case dirs not found: {missing}")
        return dirs
    return sorted(
        p for p in input_root.iterdir()
        if p.is_dir() and not p.name.endswith("_fixed")
    )


def _one_file_mode(args: argparse.Namespace) -> int:
    """Process a single file (used by subprocess isolation)."""
    input_root = args.input_root.expanduser().resolve()
    outdir_root = args.outdir_root.expanduser().resolve()
    run_mask = args.run_mask.expanduser().resolve()
    case_name = args.cases[0]
    src = input_root / case_name / args.one_file
    dst = (
        outdir_root
        / "ProcessedOutput_fixed"
        / case_name.replace("_filtered_with_coord", "")
        / args.one_file
    )
    mask = load_runmask_coords(run_mask)
    rep = fix_one_file(src, dst, mask, dry_run=False, overwrite=True)
    if rep["status"] != "ok":
        print(rep.get("error", rep["status"]), file=sys.stderr)
        return 2
    print(
        f"ONEFILE_OK time={rep['n_time']} "
        f"({rep['time_freq']} from {rep['start_year']}→{rep['time_end_year']})",
        flush=True,
    )
    return 0


def main() -> int:
    import subprocess

    args = parse_args()
    if args.one_file:
        return _one_file_mode(args)

    input_root = args.input_root.expanduser().resolve()
    outdir_root = args.outdir_root.expanduser().resolve()
    run_mask = args.run_mask.expanduser().resolve()

    if not input_root.is_dir():
        print(f"ERROR: input-root not found: {input_root}", file=sys.stderr)
        return 1
    if not run_mask.is_file():
        print(f"ERROR: run-mask not found: {run_mask}", file=sys.stderr)
        return 1

    print(f"input-root : {input_root}")
    print(f"outdir-root: {outdir_root}")
    print(f"run-mask   : {run_mask}")
    mask = load_runmask_coords(run_mask)
    print(
        f"run-mask grid: Y={mask['Y'].size} "
        f"[{float(mask['Y'][0]):.2f} .. {float(mask['Y'][-1]):.2f}], "
        f"X={mask['X'].size} "
        f"[{float(mask['X'][0]):.2f} .. {float(mask['X'][-1]):.2f}]"
    )

    case_dirs = list_case_dirs(input_root, args.cases)
    print(f"cases: {len(case_dirs)}")

    n_ok = n_skip = n_err = 0
    script = Path(__file__).resolve()
    for case_dir in case_dirs:
        case_name = case_dir.name
        out_case = outdir_root / "ProcessedOutput_fixed" / case_name.replace(
            "_filtered_with_coord", ""
        )
        for tmp in out_case.glob("*.nc.tmp"):
            try:
                tmp.unlink()
            except OSError:
                pass
        files = sorted(case_dir.glob("*.nc"))
        print(f"\n=== {case_name}  ({len(files)} files) → {out_case}/ ===", flush=True)
        for src in files:
            dst = out_case / src.name
            if dst.exists() and not args.overwrite and not args.dry_run:
                n_skip += 1
                print(f"  SKIP_EXISTS  {src.name}", flush=True)
                continue
            if args.dry_run:
                try:
                    rep = fix_one_file(src, dst, mask, dry_run=True, overwrite=True)
                    n_skip += 1
                    extra = ""
                    if "n_time" in rep:
                        extra = (
                            f" time={rep['n_time']} "
                            f"({rep.get('time_freq')} from {rep.get('start_year')})"
                        )
                    print(f"  DRY_RUN      {src.name}{extra}", flush=True)
                except Exception as exc:  # noqa: BLE001
                    n_err += 1
                    print(f"  ERROR {src.name}: {exc}", file=sys.stderr, flush=True)
                continue

            cmd = [
                sys.executable,
                str(script),
                "--input-root", str(input_root),
                "--outdir-root", str(outdir_root),
                "--run-mask", str(run_mask),
                "--cases", case_name,
                "--one-file", src.name,
                "--overwrite",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode == 0 and "ONEFILE_OK" in out:
                n_ok += 1
                shown = False
                for line in out.splitlines():
                    if line.startswith("  OK"):
                        print(line, flush=True)
                        shown = True
                        break
                if not shown:
                    detail = out.split("ONEFILE_OK", 1)[-1].strip()
                    print(f"  OK  {src.name}: {detail}", flush=True)
            else:
                n_err += 1
                err = out.strip().splitlines()[-1] if out.strip() else f"exit={proc.returncode}"
                if proc.returncode in (-11, 139):
                    err = f"segfault/HDF crash (rc={proc.returncode})"
                print(f"  ERROR {src.name}: {err}", file=sys.stderr, flush=True)
                tmp = dst.with_suffix(dst.suffix + ".tmp")
                if tmp.exists():
                    tmp.unlink()

    print(f"\nDone. ok={n_ok}  skipped/dry={n_skip}  errors={n_err}", flush=True)
    return 0 if n_err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
