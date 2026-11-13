#!/usr/bin/env python3
"""Land C change vs ctrl from local ``all_merged`` dvmdostem outputs (wetland splits).

Builds cVeg + cSoil + cCwd analogs as sum(VEGC over pft) + sum(SOC over layer) + DWDC
[g C m⁻²], converts to kg m⁻², area-weights with lat from run-mask2.nc, reports Δ vs ctrl [PgC].

Default paths use exacloud remerge + BGC rerun merges (150-year TR yearly files).

Example (1pctCO2 post-process cache on disk)::

  python3 plot_deltaCL_from_merged_cl.py --raw-cache /mnt/disks/wiemip-data/1pctCO2_processed/raw_cache \\
    --match-cou-coverage --out-dir analysis/merged_figs
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import netCDF4 as nc
import numpy as np

R_EARTH = 6.371e6
DEFAULT_LAT_MASK = Path(__file__).resolve().parents[1] / "post-processing" / "run-mask2.nc"
DEFAULT_EXA = Path("/mnt/exacloud/ejafarov_woodwellclimate_org")
DEFAULT_REMERGE = DEFAULT_EXA / "remerge"
DEFAULT_RAW_CACHE = Path("/mnt/disks/wiemip-data/1pctCO2_processed/raw_cache")
COU = ["ukesm_cou", "ipst_cou", "gfdl_cou"]
COU_RUN = {
    "ukesm_cou": "Special_cou_ukesm_WetlandOn_NitrogenOn",
    "ipst_cou": "Special_cou_ipsl_WetlandOn_NitrogenOn",
    "gfdl_cou": "Special_cou_gfdl_WetlandOn_NitrogenOn",
}
FILL = -9999.0


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exacloud-root", type=Path, default=DEFAULT_EXA)
    p.add_argument("--remerge-root", type=Path, default=DEFAULT_REMERGE)
    p.add_argument(
        "--ctrl-merged",
        type=Path,
        default=None,
        help="Path to ctrl all_merged dir (default: remerge/.../all_merged_v2)",
    )
    p.add_argument(
        "--bgc-merged",
        type=Path,
        default=None,
        help="Path to BGC all_merged (default: .../Special_bgc_..._rerun/all_merged)",
    )
    p.add_argument(
        "--raw-cache",
        type=Path,
        default=None,
        help=(
            "Post-process download cache (flat run dirs with *_tr.nc). "
            f"Default when set: {DEFAULT_RAW_CACHE}. Overrides remerge layout for ctrl/BGC/COU."
        ),
    )
    p.add_argument(
        "--cou-merged-subdir",
        default="all_merged_v3",
        help="Subdir name under each COU split in remerge (e.g. all_merged_v3); ignored if --raw-cache",
    )
    p.add_argument("--lat-mask", type=Path, default=DEFAULT_LAT_MASK)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument(
        "--match-cou-coverage",
        action="store_true",
        help="Per COU panel: mask cells finite in ctrl, BGC, and that COU (all years)",
    )
    return p.parse_args()


def cell_area(lat: np.ndarray) -> np.ndarray:
    dlat = dlon = np.deg2rad(0.5)
    lat_r = np.deg2rad(lat)
    return R_EARTH**2 * dlon * (np.sin(lat_r + dlat / 2) - np.sin(lat_r - dlat / 2))


def _to_kg_m2(arr: np.ndarray) -> np.ndarray:
    """g m⁻² → kg m⁻²; treat fill as NaN."""
    out = np.asarray(arr, dtype=np.float64)
    out = np.where(out == FILL, np.nan, out)
    return out / 1000.0


def load_land_c_stack(merged_dir: Path) -> np.ndarray:
    """Return land C [kg m⁻²], shape (time, y, x)."""
    merged_dir = Path(merged_dir)
    veg_p = merged_dir / "VEGC_yearly_tr.nc"
    soc_p = merged_dir / "SOC_yearly_tr.nc"
    cwd_p = merged_dir / "DWDC_yearly_tr.nc"
    for p in (veg_p, soc_p, cwd_p):
        if not p.is_file():
            raise FileNotFoundError(p)

    with nc.Dataset(veg_p) as dveg, nc.Dataset(soc_p) as dsoc, nc.Dataset(cwd_p) as dcwd:
        v = _to_kg_m2(dveg.variables["VEGC"][:]).sum(axis=1)  # (time, y, x)
        s = _to_kg_m2(dsoc.variables["SOC"][:]).sum(axis=1)
        c = _to_kg_m2(dcwd.variables["DWDC"][:])
        nt = min(v.shape[0], s.shape[0], c.shape[0])
        stack = np.stack([v[:nt], s[:nt], c[:nt]], axis=0)
        valid = np.any(np.isfinite(stack), axis=0)
        total = np.nansum(stack, axis=0)
        total = np.where(valid, total, np.nan)
        return total


def total_land_pg(field: np.ndarray, area: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Domain total [PgC] per time."""
    m = mask[np.newaxis, ...]
    weighted = np.where(m, field, np.nan) * area
    return np.nansum(weighted, axis=(1, 2)) / 1e12


def default_paths(args) -> dict[str, Path]:
    if args.raw_cache is not None:
        root = args.raw_cache
        ctrl = args.ctrl_merged or (root / "Special_ctrl_WetlandOn_NitrogenOn")
        bgc = args.bgc_merged or (root / "Special_bgc_WetlandOn_NitrogenOn")
        cou_map = {cou: root / COU_RUN[cou] for cou in COU}
        return {"stable_ctrl": ctrl, "stable_bgc": bgc, **cou_map}

    ctrl = args.ctrl_merged or (
        args.remerge_root / "Special_ctrl_WetlandOn_NitrogenOn_split" / "all_merged_v2"
    )
    bgc = args.bgc_merged or (
        args.exacloud_root / "Special_bgc_WetlandOn_NitrogenOn_split_rerun" / "all_merged"
    )
    cou_map = {
        "ukesm_cou": args.remerge_root
        / "Special_cou_ukesm_WetlandOn_NitrogenOn_split"
        / args.cou_merged_subdir,
        "ipst_cou": args.remerge_root
        / "Special_cou_ipsl_WetlandOn_NitrogenOn_split"
        / args.cou_merged_subdir,
        "gfdl_cou": args.remerge_root
        / "Special_cou_gfdl_WetlandOn_NitrogenOn_split"
        / args.cou_merged_subdir,
    }
    return {"stable_ctrl": ctrl, "stable_bgc": bgc, **cou_map}


def main() -> None:
    args = parse_args()
    paths = default_paths(args)
    for name, p in paths.items():
        if not p.is_dir():
            raise FileNotFoundError(f"{name}: merged dir not found: {p}")

    if not args.lat_mask.is_file():
        raise FileNotFoundError(f"lat mask: {args.lat_mask}")
    with nc.Dataset(args.lat_mask) as ds:
        area = cell_area(ds.variables["lat"][:])

    print("Merged dirs:")
    for name, p in paths.items():
        print(f"  {name}: {p}")
    print("Loading merged land C (VEGC+SOC+DWDC) …")
    fields = {name: load_land_c_stack(p) for name, p in paths.items()}
    nt = min(f.shape[0] for f in fields.values())
    fields = {n: f[:nt] for n, f in fields.items()}
    years = np.arange(nt)

    fc = fields["stable_ctrl"]
    fb = fields["stable_bgc"]

    fig, axes = plt.subplots(1, len(COU), figsize=(5 * len(COU), 4), sharey=True)
    if not args.match_cou_coverage:
        mask = np.all([np.isfinite(f).all(axis=0) for f in fields.values()], axis=0)
        print(f"common mask: {int(mask.sum())} cells")
    for ax, cou in zip(axes, COU):
        fq = fields[cou]
        if args.match_cou_coverage:
            mask = np.isfinite(fc).all(axis=0) & np.isfinite(fb).all(axis=0) & np.isfinite(fq).all(axis=0)
        ncells = int(mask.sum())
        total_c = total_land_pg(fc, area, mask)
        total_b = total_land_pg(fb, area, mask)
        total_q = total_land_pg(fq, area, mask)
        d_bgc = total_b - total_c
        d_cou = total_q - total_c
        print(
            f"  {cou}: {ncells} cells | BGC dC(0)={d_bgc[0]:+.3f} COU dC(0)={d_cou[0]:+.3f} | "
            f"BGC dC(end)={d_bgc[-1]:+.3f} COU dC(end)={d_cou[-1]:+.3f}"
        )
        ax.axvspan(60, 80, color="0.85")
        ax.axvline(70, color="0.5", ls=":", lw=0.8)
        ax.axhline(0, color="0.6", lw=0.8)
        ax.plot(years, d_bgc, color="tab:green", label="BGC")
        ax.plot(years, d_cou, color="tab:blue", label="COU")
        ax.plot(years, d_cou - d_bgc, color="tab:red", label="COU − BGC")
        ax.set_title(f"DVM_DOS_TEM ({cou})\n{ncells} cells")
        ax.set_xlabel("Year")
        ax.grid(alpha=0.3)

    axes[0].set_ylabel(r"$\Delta C_L$ (PgC)")
    axes[0].legend(loc="upper left")
    tag = "_match_cou_coverage" if args.match_cou_coverage else ""
    if args.raw_cache is not None:
        src_line = f"source=raw_cache ({args.raw_cache})"
    else:
        src_line = "ctrl=all_merged_v2 remerge; BGC=Special_bgc_*_rerun; COU=remerge all_merged_v3"
    fig.suptitle(f"Land C change vs ctrl (VEGC+SOC+DWDC){tag}\n{src_line}")
    plt.tight_layout()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"deltaCL_exacloud_merged{tag}.png"
    fig.savefig(out, dpi=200)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
