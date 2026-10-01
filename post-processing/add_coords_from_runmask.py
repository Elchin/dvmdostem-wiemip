#!/usr/bin/env python3
"""
Add X, Y, lon, lat coordinate variables from a run-mask NetCDF to WIEMIP
processed output files that currently only carry data + time.

Typical layout after download:
  ${data_dir}/${case}/wiemip_output/*.nc
or a flat directory of *.nc files.

GCS source (optional download):
  gs://wiemip/SimulationOuput/ProcessedOuput/${case}/wiemip_output/

Examples:
  # Local files already under wiemip_output (in-place)
  python add_coords_from_runmask.py \\
    --case gfdl_cou_noFire \\
    --data-dir /mnt/exacloud/$USER/wiemip/wiemip_output \\
    --run-mask /mnt/exacloud/$USER/wiemip/inputs/teminputs/new/run-mask2.nc \\
    --inplace

  # Download from GCS then write coords into a new output directory
  python add_coords_from_runmask.py \\
    --case Special_m_FireOn \\
    --gcs-prefix gs://wiemip/SimulationOuput/ProcessedOuput \\
    --data-dir /mnt/exacloud/$USER/wiemip/downloads \\
    --run-mask /mnt/exacloud/$USER/wiemip/inputs/teminputs/new/run-mask2.nc \\
    --outdir /mnt/exacloud/$USER/wiemip/wiemip_output_with_coords \\
    --download
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


COORD_NAMES = ("X", "Y", "lon", "lat")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Add X, Y, lon, lat from run-mask.nc onto processed WIEMIP NetCDF files."
        )
    )
    p.add_argument(
        "--case",
        default="",
        help=(
            "Case / experiment name (used for GCS path and optional "
            "subdir under --data-dir). Leave empty if --data-dir already "
            "points at the folder of *.nc files."
        ),
    )
    p.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help=(
            "Local directory containing the NetCDF files, or the parent "
            "into which GCS data is downloaded. If --case is set and "
            "${data-dir}/${case}/wiemip_output exists, that folder is used."
        ),
    )
    p.add_argument(
        "--run-mask",
        required=True,
        type=Path,
        help="Path to run-mask NetCDF with variables X, Y, lon, lat.",
    )
    p.add_argument(
        "--gcs-prefix",
        default="gs://wiemip/SimulationOuput/ProcessedOuput",
        help=(
            "GCS prefix (without trailing case). Download path becomes "
            "${gcs-prefix}/${case}/wiemip_output/"
        ),
    )
    p.add_argument(
        "--download",
        action="store_true",
        help="Download *.nc from GCS into --data-dir before adding coords.",
    )
    p.add_argument(
        "--inplace",
        action="store_true",
        help="Modify NetCDF files in place (default: write under --outdir).",
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Directory for output files when not using --inplace.",
    )
    p.add_argument(
        "--pattern",
        default="*.nc",
        help="Glob for input files (default: *.nc).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; do not download or write files.",
    )
    p.add_argument(
        "--overwrite-coords",
        action="store_true",
        help="Replace existing X/Y/lon/lat variables if already present.",
    )
    return p.parse_args()


def resolve_input_dir(data_dir: Path, case: str) -> Path:
    """Prefer ${data_dir}/${case}/wiemip_output if it exists."""
    data_dir = data_dir.expanduser().resolve()
    if case:
        nested = data_dir / case / "wiemip_output"
        if nested.is_dir():
            return nested
        # after gsutil -m cp -r .../wiemip_output data_dir/
        flat_case = data_dir / "wiemip_output"
        if flat_case.is_dir():
            return flat_case
    return data_dir


def gcs_uri(gcs_prefix: str, case: str) -> str:
    if not case:
        raise SystemExit("--case is required with --download")
    return f"{gcs_prefix.rstrip('/')}/{case}/wiemip_output/"


def download_from_gcs(uri: str, data_dir: Path, dry_run: bool) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["gsutil", "-m", "cp", "-r", uri, str(data_dir)]
    print("[download]", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def load_coords(run_mask: Path):
    with Dataset(run_mask) as ds:
        missing = [n for n in COORD_NAMES if n not in ds.variables]
        if missing:
            raise SystemExit(f"{run_mask} missing variables: {missing}")
        if "Y" not in ds.dimensions or "X" not in ds.dimensions:
            raise SystemExit(f"{run_mask} missing Y/X dimensions")
        coords = {
            "Y": np.asarray(ds.variables["Y"][:]),
            "X": np.asarray(ds.variables["X"][:]),
            "lat": np.asarray(ds.variables["lat"][:]),
            "lon": np.asarray(ds.variables["lon"][:]),
        }
        attrs = {
            name: {
                a: getattr(ds.variables[name], a)
                for a in ds.variables[name].ncattrs()
                if a != "_FillValue"
            }
            for name in COORD_NAMES
        }
        n_y = int(ds.dimensions["Y"].size)
        n_x = int(ds.dimensions["X"].size)
    if coords["lat"].shape != (n_y, n_x) or coords["lon"].shape != (n_y, n_x):
        raise SystemExit(
            f"lat/lon shape {coords['lat'].shape}/{coords['lon'].shape} "
            f"!= ({n_y}, {n_x})"
        )
    return coords, attrs, n_y, n_x


def find_yx_dims(ds: Dataset) -> tuple[str, str]:
    """Map spatial dims in the data file to run-mask Y/X sizes."""
    names = {k.lower(): k for k in ds.dimensions}
    # Prefer lowercase y/x used by processed WIEMIP outputs
    for y_cand, x_cand in (("y", "x"), ("Y", "X"), ("lat", "lon")):
        if y_cand in ds.dimensions and x_cand in ds.dimensions:
            return y_cand, x_cand
        if y_cand.lower() in names and x_cand.lower() in names:
            return names[y_cand.lower()], names[x_cand.lower()]
    raise SystemExit(
        f"Could not find y/x (or Y/X) dimensions in file; have {list(ds.dimensions)}"
    )


def copy_attrs(dst_var, attrs: dict) -> None:
    for key, val in attrs.items():
        try:
            setattr(dst_var, key, val)
        except Exception:
            pass


def add_coords_to_file(
    src: Path,
    dst: Path,
    coords: dict,
    attrs: dict,
    n_y: int,
    n_x: int,
    *,
    overwrite: bool,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"[dry-run] add coords -> {dst}")
        return

    if src.resolve() != dst.resolve():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    with Dataset(dst, "a") as ds:
        y_dim, x_dim = find_yx_dims(ds)
        if int(ds.dimensions[y_dim].size) != n_y or int(ds.dimensions[x_dim].size) != n_x:
            raise SystemExit(
                f"{src.name}: spatial shape "
                f"({ds.dimensions[y_dim].size}, {ds.dimensions[x_dim].size}) "
                f"!= run-mask ({n_y}, {n_x})"
            )

        # 1-D Y / X
        for name, dim, data in (
            ("Y", y_dim, coords["Y"]),
            ("X", x_dim, coords["X"]),
        ):
            if name in ds.variables:
                if not overwrite:
                    print(f"  skip existing {name} in {dst.name}")
                    continue
                ds.variables[name][:] = data
                copy_attrs(ds.variables[name], attrs[name])
            else:
                var = ds.createVariable(name, data.dtype, (dim,))
                var[:] = data
                copy_attrs(var, attrs[name])

        # 2-D lat / lon
        for name in ("lat", "lon"):
            data = coords[name]
            if name in ds.variables:
                if not overwrite:
                    print(f"  skip existing {name} in {dst.name}")
                    continue
                ds.variables[name][:] = data
                copy_attrs(ds.variables[name], attrs[name])
            else:
                var = ds.createVariable(name, data.dtype, (y_dim, x_dim))
                var[:] = data
                copy_attrs(var, attrs[name])

    print(f"  wrote coords -> {dst}")


def main() -> int:
    args = parse_args()
    run_mask = args.run_mask.expanduser().resolve()
    if not run_mask.is_file():
        raise SystemExit(f"run-mask not found: {run_mask}")

    data_dir = args.data_dir.expanduser()
    if args.download:
        uri = gcs_uri(args.gcs_prefix, args.case)
        download_from_gcs(uri, data_dir, args.dry_run)

    input_dir = resolve_input_dir(data_dir, args.case)
    if not args.dry_run and not input_dir.is_dir():
        raise SystemExit(f"input directory not found: {input_dir}")

    if args.inplace:
        outdir = input_dir
    else:
        if args.outdir is None:
            raise SystemExit("Provide --outdir or pass --inplace")
        outdir = args.outdir.expanduser().resolve()

    print(f"case      = {args.case or '<none>'}")
    print(f"input_dir = {input_dir}")
    print(f"run_mask  = {run_mask}")
    print(f"outdir    = {outdir} ({'inplace' if args.inplace else 'copy'})")

    coords, attrs, n_y, n_x = load_coords(run_mask)
    print(f"run-mask grid: Y={n_y}, X={n_x}")

    files = sorted(input_dir.glob(args.pattern)) if input_dir.is_dir() else []
    if not files and not args.dry_run:
        raise SystemExit(f"No files matching {args.pattern} under {input_dir}")
    print(f"files     = {len(files)}")

    for src in files:
        dst = src if args.inplace else outdir / src.name
        try:
            add_coords_to_file(
                src,
                dst,
                coords,
                attrs,
                n_y,
                n_x,
                overwrite=args.overwrite_coords,
                dry_run=args.dry_run,
            )
        except SystemExit as exc:
            print(f"ERROR {src.name}: {exc}", file=sys.stderr)
            return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
