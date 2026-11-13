#!/usr/bin/env python3
"""Build 2-D wetland merge masks from 1pctCO2 raw_cache (VEGC+SOC+DWDC coverage)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import netCDF4 as nc
import numpy as np

_ANALYSIS = Path(__file__).resolve().parents[1] / "analysis"
if str(_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS))
from plot_deltaCL_from_merged_cl import load_land_c_stack  # noqa: E402

DEFAULT_CACHE = Path("/mnt/disks/wiemip-data/1pctCO2_processed/raw_cache")
DEFAULT_OUT = Path(__file__).resolve().parent / "wetland_merge_masks"

WET_NITROGEN = {
    "ctrl": "Special_ctrl_WetlandOn_NitrogenOn",
    "bgc": "Special_bgc_WetlandOn_NitrogenOn",
    "ukesm": "Special_cou_ukesm_WetlandOn_NitrogenOn",
    "ipsl": "Special_cou_ipsl_WetlandOn_NitrogenOn",
    "gfdl": "Special_cou_gfdl_WetlandOn_NitrogenOn",
}

WET_NO_N = {
    "ctrl": "Special_ctrl_WetlandOn",
    "bgc": "Special_bgc_WetlandOn",
    "ukesm": "Special_cou_ukesm_WetlandOn",
    "ipsl": "Special_cou_ipsl_WetlandOn",
    "gfdl": "Special_cou_gfdl_WetlandOn",
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-cache", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--family", choices=["nitrogen_on", "no_nitrogen", "both"], default="both")
    return p.parse_args()


def wet_land_c_valid(wet_dir: Path) -> np.ndarray:
    """True where land C from load_land_c_stack is finite every year."""
    field = load_land_c_stack(Path(wet_dir))
    return np.isfinite(field).all(axis=0)


def write_mask(path: Path, mask: np.ndarray, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    ny, nx = mask.shape
    with nc.Dataset(path, "w") as ds:
        ds.createDimension("y", ny)
        ds.createDimension("x", nx)
        v = ds.createVariable("merge_mask", "i8", ("y", "x"))
        v.long_name = title
        v[:] = mask.astype(np.int8)
    print(f"Wrote {path} ({int(mask.sum())} / {mask.size} cells)")


def build_family(cache: Path, out_dir: Path, wet_map: dict[str, str], tag: str) -> None:
    valid = {k: wet_land_c_valid(cache / name) for k, name in wet_map.items()}
    ctrl_bgc = valid["ctrl"] & valid["bgc"]
    write_mask(out_dir / f"merge_mask_{tag}_ctrl_bgc.nc", ctrl_bgc, f"{tag} ctrl∩bgc wetland land C valid")
    for cou in ("ukesm", "ipsl", "gfdl"):
        m = ctrl_bgc & valid[cou]
        write_mask(out_dir / f"merge_mask_{tag}_{cou}.nc", m, f"{tag} ctrl∩bgc∩{cou} wetland land C valid")


def main() -> None:
    args = parse_args()
    if args.family in ("nitrogen_on", "both"):
        build_family(args.raw_cache, args.out_dir, WET_NITROGEN, "nitrogen_on")
    if args.family in ("no_nitrogen", "both"):
        build_family(args.raw_cache, args.out_dir, WET_NO_N, "no_nitrogen")


if __name__ == "__main__":
    main()
