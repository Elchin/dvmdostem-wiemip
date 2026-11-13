import argparse
import glob
import os

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

DEFAULT_BASE = "/mnt/disks/wiemip-data/1pctCO2_processed"
DEFAULT_OUT = "/mnt/disks/wiemip-data/dvmdostem-wiemip/analysis/1pctCO2_new_figs"
POOLS = ["cVeg", "cSoil", "cCwd"]
COU = ["ukesm_cou", "ipst_cou", "gfdl_cou"]
R_EARTH = 6.371e6


def parse_args():
    p = argparse.ArgumentParser(description="DVM-DOS-TEM 1pctCO2 land carbon change (exp - ctrl), PgC.")
    p.add_argument("--source", default="filtered_with_coord", choices=["filtered_with_coord", "wiemip_output"])
    p.add_argument("--suffix", default="", help="Scenario suffix, e.g. _noFire")
    p.add_argument("--common_mask", action="store_true", help="Restrict all runs to cells valid in every run")
    p.add_argument(
        "--match_cou_coverage",
        action="store_true",
        help="Per COU panel: mask to cells finite in stable_ctrl, stable_bgc, and that COU (all time steps); BGC uses same mask as that panel",
    )
    p.add_argument(
        "--cou_t0_adjust_row",
        action="store_true",
        help="With --match_cou_coverage: add a second row of panels with COU shifted by -ΔC_COU(0) (COU starts at 0); BGC unchanged",
    )
    p.add_argument("--base", default=DEFAULT_BASE, help="Root dir with DVM-DOS-TEM_* case folders")
    p.add_argument("--out-dir", default=DEFAULT_OUT, help="Directory for output PNG")
    p.add_argument("--out-file", default=None, help="Full path for output PNG (overrides out-dir naming)")
    return p.parse_args()


def cell_area(lat):
    dlat = dlon = np.deg2rad(0.5)
    lat_r = np.deg2rad(lat)
    return R_EARTH**2 * dlon * (np.sin(lat_r + dlat / 2) - np.sin(lat_r - dlat / 2))


def load_pool(scenario, pool, source, base):
    path = glob.glob(f"{base}/DVM-DOS-TEM_{scenario}/{source}/*_{pool}_yr_*.nc")[0]
    return xr.open_dataset(path, decode_times=False)[pool].values


def land_carbon(scenario, source, base):
    """Total land carbon per cell [kg C m-2], shape (time, y, x)."""
    arrays = [load_pool(scenario, p, source, base) for p in POOLS]
    nt = min(a.shape[0] for a in arrays)
    return sum(a[:nt] for a in arrays)


def total_land_pg(f, area, mask):
    """Domain total land C [PgC] per time; mask (y,x) bool, cells outside mask excluded."""
    return np.nansum(np.where(mask, f, np.nan) * area, axis=(1, 2)) / 1e12


def main():
    args = parse_args()
    base = args.base
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    lat_path = glob.glob(f"{base}/DVM-DOS-TEM_stable_ctrl/filtered_with_coord/*_cVeg_yr_*.nc")[0]
    area = cell_area(xr.open_dataset(lat_path, decode_times=False)["lat"].values)

    names = ["stable_ctrl", "stable_bgc"] + COU
    suffixes = {n: args.suffix for n in names}
    if args.suffix.lower() == "_nonitrogen":
        suffixes = {n: ("_noNitrogen" if n == "stable_ctrl" else "_noNItrogen") for n in names}
    fields = {n: land_carbon(n + suffixes[n], args.source, base) for n in names}
    nt = min(f.shape[0] for f in fields.values())
    fields = {n: f[:nt] for n, f in fields.items()}

    if args.common_mask and not args.match_cou_coverage:
        mask = np.all([np.isfinite(f).all(axis=0) for f in fields.values()], axis=0)
        fields = {n: np.where(mask, f, np.nan) for n, f in fields.items()}

    years = np.arange(nt)

    if args.match_cou_coverage:
        fc = fields["stable_ctrl"]
        fb = fields["stable_bgc"]
        print("match_cou_coverage: per-panel mask = finite(ctrl) & finite(bgc) & finite(that COU), all time steps")
        nrows = 2 if args.cou_t0_adjust_row else 1
        fig, axes = plt.subplots(
            nrows, len(COU), figsize=(5 * len(COU), 4 * nrows), sharex=True, sharey="row"
        )
        if nrows == 1:
            axes = axes[np.newaxis, :]
        panel_data = []
        for cou in COU:
            fq = fields[cou]
            mask = (
                np.isfinite(fc).all(axis=0)
                & np.isfinite(fb).all(axis=0)
                & np.isfinite(fq).all(axis=0)
            )
            ncells = int(mask.sum())
            total_c = total_land_pg(fc, area, mask)
            total_b = total_land_pg(fb, area, mask)
            total_q = total_land_pg(fq, area, mask)
            d_bgc = total_b - total_c
            d_cou = total_q - total_c
            panel_data.append((cou, ncells, d_bgc, d_cou))
            print(
                f"  panel {cou}: {ncells} cells | BGC dC(0)={d_bgc[0]:+.2f} COU dC(0)={d_cou[0]:+.2f} | "
                f"BGC dC(end)={d_bgc[-1]:+.2f} COU dC(end)={d_cou[-1]:+.2f}"
            )

        def draw_panel(ax, cou, ncells, d_bgc, d_cou, row_label):
            ax.axvspan(60, 80, color="0.85")
            ax.axvline(70, color="0.5", ls=":", lw=0.8)
            ax.axhline(0, color="0.6", lw=0.8)
            ax.plot(years, d_bgc, color="tab:green", label="BGC")
            ax.plot(years, d_cou, color="tab:blue", label="COU")
            ax.plot(years, d_cou - d_bgc, color="tab:red", label="COU - BGC")
            ax.set_title(f"DVM_DOS_TEM ({cou})\n{ncells} cells{row_label}")
            if ax.get_subplotspec().rowspan.stop == nrows:
                ax.set_xlabel("Year")
            ax.grid(alpha=0.3)

        for j, (cou, ncells, d_bgc, d_cou) in enumerate(panel_data):
            draw_panel(axes[0, j], cou, ncells, d_bgc, d_cou, "")
        axes[0, 0].set_ylabel(r"$\Delta C_L$ (PgC)")
        axes[0, 0].legend(loc="upper left")

        if args.cou_t0_adjust_row:
            for j, (cou, ncells, d_bgc, d_cou) in enumerate(panel_data):
                d_cou_adj = d_cou - d_cou[0]
                print(
                    f"  panel {cou} (COU t0-adj): COU dC'(0)={d_cou_adj[0]:+.2f} | "
                    f"COU dC'(end)={d_cou_adj[-1]:+.2f} | COU-BGC at end={(d_cou_adj - d_bgc)[-1]:+.2f}"
                )
                draw_panel(
                    axes[1, j],
                    cou,
                    ncells,
                    d_bgc,
                    d_cou_adj,
                    "\nCOU: ΔC(t) − ΔC(0)",
                )
            axes[1, 0].set_ylabel(r"$\Delta C_L$ (PgC)")
            if nrows > 1:
                axes[1, 0].legend(loc="upper left")

        mask_tag = "_match_cou_coverage"
        if args.common_mask:
            print("Note: --common_mask is ignored when --match_cou_coverage is set (per-panel mask is already stricter).")
        subtitle = "Mask: cells with valid {pools} for ctrl, BGC, and each COU".format(pools=", ".join(POOLS))
        if args.cou_t0_adjust_row:
            subtitle += "\nLower row: COU curve shifted by −ΔC_COU(0); BGC and mask unchanged"
        fig.suptitle(
            f"Land C change vs ctrl ({'+'.join(POOLS)}), source={args.source}{args.suffix}{mask_tag}\n"
            f"{subtitle}"
        )
        plt.tight_layout()
        out = args.out_file or os.path.join(out_dir, f"1pctCO2_deltaCL_{args.source}{args.suffix}{mask_tag}.png")
        plt.savefig(out, dpi=200)
        print(f"Saved {out}")
        return

    total = {n: np.nansum(f * area, axis=(1, 2)) / 1e12 for n, f in fields.items()}  # PgC
    d_bgc = total["stable_bgc"] - total["stable_ctrl"]

    print(f"{'run':12s} C(t=0) [PgC]  dC(t=0)  dC(end)")
    for n in names:
        d = total[n] - total["stable_ctrl"]
        print(f"{n:12s} {total[n][0]:10.1f} {d[0]:+8.2f} {d[-1]:+8.2f}")

    fig, axes = plt.subplots(1, len(COU), figsize=(5 * len(COU), 4), sharey=True)
    for ax, cou in zip(axes, COU):
        d_cou = total[cou] - total["stable_ctrl"]
        ax.axvspan(60, 80, color="0.85")
        ax.axvline(70, color="0.5", ls=":", lw=0.8)
        ax.axhline(0, color="0.6", lw=0.8)
        ax.plot(years, d_bgc, color="tab:green", label="BGC")
        ax.plot(years, d_cou, color="tab:blue", label="COU")
        ax.plot(years, d_cou - d_bgc, color="tab:red", label="COU - BGC")
        ax.set_title(f"DVM_DOS_TEM ({cou})")
        ax.set_xlabel("Year")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(r"$\Delta C_L$ (PgC)")
    axes[0].legend(loc="upper left")
    mask_tag = "_commonmask" if args.common_mask else ""
    fig.suptitle(f"Land C change vs ctrl ({'+'.join(POOLS)}), source={args.source}{args.suffix}{mask_tag}")
    plt.tight_layout()
    out = args.out_file or os.path.join(out_dir, f"1pctCO2_deltaCL_{args.source}{args.suffix}{mask_tag}.png")
    plt.savefig(out, dpi=200)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
