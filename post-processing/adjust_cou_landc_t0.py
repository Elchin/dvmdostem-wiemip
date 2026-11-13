#!/usr/bin/env python3
"""
Align COU land-carbon pools to stable_ctrl at t=0 in filtered_with_coord.

For each pool in {cVeg, cSoil, cCwd}, at every grid cell where both COU and
ctrl are finite at year index 0:

    C_COU'(t) = C_COU(t) - (C_COU(0) - C_ctrl(0))

Domain totals of (cVeg+cSoil+cCwd) vs the matching stable_ctrl case then have
ΔC(0) ≈ 0 when users plot COU minus ctrl (same mask as in analysis figures).

Only COU cases are modified (in place under filtered_with_coord/). Writes
README.md in each adjusted filtered_with_coord/ folder.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
from datetime import datetime, timezone

import numpy as np
import xarray as xr

POOLS = ("cVeg", "cSoil", "cCwd")
README_NAME = "README.md"
README_BODY = """# `filtered_with_coord` — COU land-C t=0 alignment

These NetCDFs were post-processed so WIEMIP land carbon pools match the
paired **stable_ctrl** run at the first time step (year index 0).

## Pools adjusted

`cVeg`, `cSoil`, `cCwd` (annual `*_yr_05.nc` files in this directory).

## Transform (per grid cell, where COU and ctrl are finite at t=0)

```
C_COU'(t) = C_COU(t) - (C_COU(0) - C_ctrl(0))
```

Other variables in this folder are unchanged. This is a **plotting convenience**
for ΔC vs ctrl; it does not re-balance carbon across pools or fix underlying
merge/restart mismatches.

## Reference ctrl case

`{ctrl_case}`

## Pipeline

Script: `dvmdostem-wiemip/post-processing/adjust_cou_landc_t0.py`

Applied: {applied_utc}
"""


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--base",
        default="/mnt/disks/wiemip-data/1pctCO2_processed_matchmerge",
        help="Root with DVM-DOS-TEM_<case>/filtered_with_coord/",
    )
    p.add_argument(
        "--case",
        action="append",
        default=None,
        help="Case folder name (e.g. DVM-DOS-TEM_ukesm_cou_noFire); repeat or omit with --case-pattern",
    )
    p.add_argument(
        "--case-pattern",
        default=r".*_cou_noFire$",
        help="Regex on case folder basename when --case not set (default: *_cou_noFire)",
    )
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def ctrl_case_for(cou_case: str) -> str:
    """DVM-DOS-TEM_ukesm_cou_noFire -> DVM-DOS-TEM_stable_ctrl_noFire."""
    rest = cou_case.removeprefix("DVM-DOS-TEM_")
    if not rest.endswith("_cou") and "_cou_" in rest:
        suffix = rest.split("_cou", 1)[1]
        return f"DVM-DOS-TEM_stable_ctrl{suffix}"
    if rest.endswith("_cou"):
        return "DVM-DOS-TEM_stable_ctrl"
    raise ValueError(f"Not a COU case name: {cou_case}")


def pool_glob(base: str, case: str, pool: str) -> str:
    hits = glob.glob(f"{base}/{case}/filtered_with_coord/*_{pool}_yr_*.nc")
    if len(hits) != 1:
        raise FileNotFoundError(f"{case}: expected one {pool} file, got {hits}")
    return hits[0]


def adjust_pool(cou_path: str, ctrl_path: str, pool: str, dry_run: bool) -> None:
    with xr.open_dataset(cou_path, decode_times=False) as dsc, xr.open_dataset(
        ctrl_path, decode_times=False
    ) as ds0:
        if pool not in dsc or pool not in ds0:
            raise KeyError(f"{pool} missing in {cou_path} or {ctrl_path}")
        cou = dsc[pool].values
        ctrl0 = ds0[pool].values[0]
        offset = cou[0] - ctrl0
        mask = np.isfinite(cou[0]) & np.isfinite(ctrl0)
        adj = cou.copy()
        adj[:, mask] = adj[:, mask] - offset[mask]
        if dry_run:
            print(f"  [dry-run] would adjust {os.path.basename(cou_path)} ({int(mask.sum())} cells)")
            return
        dsc[pool].values = adj
        dsc.attrs["cou_landc_t0_adjusted"] = "true"
        dsc.attrs["cou_landc_t0_adjust_reference"] = os.path.basename(os.path.dirname(os.path.dirname(ctrl_path)))
        dsc.attrs["cou_landc_t0_adjust_pools"] = ",".join(POOLS)
        tmp = cou_path + ".tmp.nc"
        dsc.to_netcdf(tmp)
        os.replace(tmp, cou_path)
        print(f"  adjusted {os.path.basename(cou_path)} ({int(mask.sum())} cells)")


def write_readme(out_dir: str, ctrl_case: str, dry_run: bool) -> None:
    path = os.path.join(out_dir, README_NAME)
    body = README_BODY.format(
        ctrl_case=ctrl_case,
        applied_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    if dry_run:
        print(f"  [dry-run] would write {path}")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"  wrote {path}")


def list_cases(base: str, case_args: list[str] | None, pattern: str) -> list[str]:
    if case_args:
        return case_args
    rx = re.compile(pattern)
    out = []
    for name in sorted(os.listdir(base)):
        if not name.startswith("DVM-DOS-TEM_"):
            continue
        if not os.path.isdir(os.path.join(base, name, "filtered_with_coord")):
            continue
        if rx.search(name):
            out.append(name)
    return out


def main() -> int:
    args = parse_args()
    cases = list_cases(args.base, args.case, args.case_pattern)
    if not cases:
        raise SystemExit("No cases matched")
    print(f"base={args.base} cases={len(cases)}")
    for case in cases:
        ctrl = ctrl_case_for(case)
        fwc = os.path.join(args.base, case, "filtered_with_coord")
        print(f"\n{case} -> ctrl {ctrl}")
        for pool in POOLS:
            cou_p = pool_glob(args.base, case, pool)
            ctrl_p = pool_glob(args.base, ctrl, pool)
            adjust_pool(cou_p, ctrl_p, pool, args.dry_run)
        write_readme(fwc, ctrl, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
