#!/usr/bin/env python3
"""
Batch-process all WIEMIP cases under:
  gs://wiemip/SimulationOuput/ProcessedOuput/DVM-DOS-TEM*/wiemip_output/*.nc

For each case:
  1) download wiemip_output/*.nc from GCS
  2) add X/Y/lon/lat via add_coords_from_runmask.py
  3) write results to ${work_root}/${case}/<original_filename>.nc

Examples:
  # Process all DVM-DOS-TEM* cases
  python process_all_cases_add_coords.py \\
    --work-root /mnt/exacloud/$USER/wiemip/processed_with_coords \\
    --run-mask /mnt/exacloud/$USER/wiemip/inputs/teminputs/new/run-mask2.nc

  # Dry-run (list cases / commands only)
  python process_all_cases_add_coords.py --work-root /tmp/test --dry-run

  # One case only
  python process_all_cases_add_coords.py \\
    --work-root /mnt/exacloud/$USER/wiemip/processed_with_coords \\
    --case DVM-DOS-TEM_gfdl_cou_noFire
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_GCS_PREFIX = "gs://wiemip/SimulationOuput/ProcessedOuput"
DEFAULT_CASE_GLOB = "DVM-DOS-TEM*"
SCRIPT_DIR = Path(__file__).resolve().parent
ADD_COORDS = SCRIPT_DIR / "add_coords_from_runmask.py"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Download each DVM-DOS-TEM* case from GCS, add run-mask coords, "
            "and save under ${case}/ with original filenames."
        )
    )
    p.add_argument(
        "--work-root",
        type=Path,
        required=True,
        help=(
            "Local root for downloads and outputs. Creates "
            "${work-root}/_downloads/${case}/ and "
            "${work-root}/${case}/."
        ),
    )
    p.add_argument(
        "--run-mask",
        type=Path,
        default=Path(
            "/mnt/exacloud/cchang_woodwellclimate_org/wiemip/"
            "inputs/teminputs/new/run-mask2.nc"
        ),
        help="run-mask NetCDF with X, Y, lon, lat.",
    )
    p.add_argument(
        "--gcs-prefix",
        default=DEFAULT_GCS_PREFIX,
        help=f"GCS parent prefix (default: {DEFAULT_GCS_PREFIX}).",
    )
    p.add_argument(
        "--case-glob",
        default=DEFAULT_CASE_GLOB,
        help=f"Case directory glob under GCS prefix (default: {DEFAULT_CASE_GLOB}).",
    )
    p.add_argument(
        "--case",
        action="append",
        default=[],
        help="Process only this case name (repeatable). Default: all matching glob.",
    )
    p.add_argument(
        "--path-to-case",
        type=Path,
        default=None,
        help="Local path to a folder containing .nc files to process directly without GCS download.",
    )
    p.add_argument(
        "--add-coords-script",
        type=Path,
        default=ADD_COORDS,
        help="Path to add_coords_from_runmask.py",
    )
    p.add_argument(
        "--keep-downloads",
        action="store_true",
        help="Keep downloaded raw files under _downloads/ (default: delete after success).",
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip a case if ${case}/ already has *.nc files.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List cases and planned paths only; do not download or write.",
    )
    return p.parse_args()


def run(cmd: list[str], dry_run: bool = False) -> None:
    printable = " ".join(cmd)
    print(f"[RUN] {printable}")
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def list_cases(gcs_prefix: str, case_glob: str) -> list[str]:
    pattern = f"{gcs_prefix.rstrip('/')}/{case_glob}/"
    cmd = ["gsutil", "ls", "-d", pattern]
    print(f"[LIST] {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    cases = []
    for line in result.stdout.splitlines():
        line = line.strip().rstrip("/")
        if not line:
            continue
        name = line.rsplit("/", 1)[-1]
        if name.startswith("DVM-DOS-TEM"):
            cases.append(name)
    return sorted(set(cases))


def case_has_wiemip_output(gcs_prefix: str, case: str) -> bool:
    uri = f"{gcs_prefix.rstrip('/')}/{case}/wiemip_output/"
    result = subprocess.run(
        ["gsutil", "ls", uri],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return False
    return any(line.strip().endswith(".nc") for line in result.stdout.splitlines())


def process_case(
    case: str,
    *,
    work_root: Path,
    run_mask: Path,
    gcs_prefix: str,
    add_coords_script: Path,
    keep_downloads: bool,
    skip_existing: bool,
    dry_run: bool,
) -> None:
    download_dir = work_root / "_downloads" / case
    # gsutil cp -r gs://.../wiemip_output download_dir  -> download_dir/wiemip_output/*.nc
    raw_nc_dir = download_dir / "wiemip_output"
    out_dir = work_root / case
    gcs_uri = f"{gcs_prefix.rstrip('/')}/{case}/wiemip_output/"

    print()
    print("=" * 72)
    print(f"CASE: {case}")
    print(f"  GCS       = {gcs_uri}")
    print(f"  download  = {raw_nc_dir}")
    print(f"  outdir    = {out_dir}")
    print("=" * 72)

    if skip_existing and out_dir.is_dir() and any(out_dir.glob("*.nc")):
        print(f"[SKIP] {out_dir} already has NetCDF files")
        return

    if not dry_run and not case_has_wiemip_output(gcs_prefix, case):
        print(f"[SKIP] no *.nc under {gcs_uri}")
        return

    # 1) download
    if not dry_run:
        download_dir.mkdir(parents=True, exist_ok=True)
    run(["gsutil", "-m", "cp", "-r", gcs_uri, str(download_dir)], dry_run=dry_run)

    if not dry_run:
        if not raw_nc_dir.is_dir():
            raise SystemExit(f"Expected download dir missing: {raw_nc_dir}")
        n_in = len(list(raw_nc_dir.glob("*.nc")))
        if n_in == 0:
            raise SystemExit(f"No *.nc downloaded into {raw_nc_dir}")
        print(f"[INFO] downloaded {n_in} NetCDF files")

    # 2) add coords -> ${case}/<original name>
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    run(
        [
            sys.executable,
            str(add_coords_script),
            "--data-dir",
            str(raw_nc_dir),
            "--run-mask",
            str(run_mask),
            "--outdir",
            str(out_dir),
            "--overwrite-coords",
        ],
        dry_run=dry_run,
    )

    if not dry_run:
        n_out = len(list(out_dir.glob("*.nc")))
        print(f"[INFO] wrote {n_out} files to {out_dir}")

    # 3) cleanup raw download unless kept
    if keep_downloads:
        print(f"[KEEP] downloads at {download_dir}")
    else:
        if dry_run:
            print(f"[dry-run] rm -rf {download_dir}")
        else:
            shutil.rmtree(download_dir, ignore_errors=True)
            print(f"[CLEAN] removed {download_dir}")


def main() -> int:
    args = parse_args()
    work_root = args.work_root.expanduser().resolve()
    run_mask = args.run_mask.expanduser().resolve()
    add_script = args.add_coords_script.expanduser().resolve()

    if not add_script.is_file():
        raise SystemExit(f"add-coords script not found: {add_script}")
    if not args.dry_run and not run_mask.is_file():
        print(f"[INFO] {run_mask} not found. Downloading from gs://wiemip/teminputs/new/run-mask2.nc...")
        run_mask.parent.mkdir(parents=True, exist_ok=True)
        run(["gsutil", "cp", "gs://wiemip/teminputs/new/run-mask2.nc", str(run_mask)])
        if not run_mask.is_file():
            raise SystemExit(f"run-mask still not found after download attempt: {run_mask}")

    if args.path_to_case:
        input_dir = args.path_to_case.expanduser().resolve()
        out_dir = work_root
        
        print()
        print("=" * 72)
        print(f"LOCAL DIRECTORY: {input_dir}")
        print(f"  outdir       = {out_dir}")
        print("=" * 72)
        
        if not args.dry_run and not input_dir.is_dir():
            raise SystemExit(f"Provided --path-to-case is not a directory: {input_dir}")
            
        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            
        run(
            [
                sys.executable,
                str(add_script),
                "--data-dir",
                str(input_dir),
                "--run-mask",
                str(run_mask),
                "--outdir",
                str(out_dir),
                "--overwrite-coords",
            ],
            dry_run=args.dry_run,
        )
        print(f"Finished processing local directory: {input_dir}")
        return 0

    if args.case:
        cases = args.case
    else:
        cases = list_cases(args.gcs_prefix, args.case_glob)

    if not cases:
        raise SystemExit("No cases found to process.")

    print(f"work_root = {work_root}")
    print(f"run_mask  = {run_mask}")
    print(f"cases     = {len(cases)}")
    for c in cases:
        print(f"  - {c}")

    if not args.dry_run:
        work_root.mkdir(parents=True, exist_ok=True)

    failed: list[str] = []
    for case in cases:
        try:
            process_case(
                case,
                work_root=work_root,
                run_mask=run_mask,
                gcs_prefix=args.gcs_prefix,
                add_coords_script=add_script,
                keep_downloads=args.keep_downloads,
                skip_existing=args.skip_existing,
                dry_run=args.dry_run,
            )
        except (subprocess.CalledProcessError, SystemExit) as exc:
            print(f"[ERROR] {case}: {exc}", file=sys.stderr)
            failed.append(case)

    print()
    print("=" * 72)
    print(f"Finished. ok={len(cases) - len(failed)} / {len(cases)}")
    if failed:
        print("Failed cases:")
        for c in failed:
            print(f"  - {c}")
        return 1
    print(f"Outputs under: {work_root}/<case>/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
