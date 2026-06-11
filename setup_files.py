#!/usr/bin/env python3
import os
import subprocess
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Setup experiment files from GCS.")
    parser.add_argument(
        "--dest-folder",
        type=str,
        default="/mnt/exacloud/ext_ejafarov_woodwellclimate_org",
        help="Base destination folder where the experiment folder will be created."
    )
    parser.add_argument(
        "--folder",
        type=str,
        default="Exp_spin_noFire",
        help="Target folder name to create inside the destination folder."
    )
    
    # Check if a positional or specific flag like --Exp_spin_noFire was passed
    # as a shorthand.
    args, unknown = parser.parse_known_args()
    
    # If the user passes something like --Exp_spin_noFire, we can treat it as the folder name.
    for arg in unknown:
        if arg.startswith("--") and len(arg) > 2:
            args.folder = arg[2:]
            break

    base_dir = args.dest_folder
    target_dir = os.path.join(base_dir, args.folder)

    print(f"Creating target directory: {target_dir}")
    os.makedirs(target_dir, exist_ok=True)

    mappings = [
        ("gs://wiemip/teminputs/co2_const.nc", "co2.nc"),
        ("gs://wiemip/teminputs/drainage_stable.nc", "drainage.nc"),
        ("gs://wiemip/teminputs/explicit-fire_stable.nc", "historic-explicit-fire.nc"),
        ("gs://wiemip/teminputs/fri-fire_stable.nc", "fri-fire.nc"),
        ("gs://wiemip/teminputs/new/run-mask2.nc", "run-mask.nc"),
        ("gs://wiemip/teminputs/new/texture.nc", "soil-texture.nc"),
        ("gs://wiemip/teminputs/new/topo.nc", "topo.nc"),
        ("gs://wiemip/teminputs/new/wetland.nc", "vegetation.nc"),
        ("gs://wiemip/teminputs/new/ch4_input", "."),
        ("gs://wiemip/spinup_noFire_noWetland/climate_stable_150yr.nc", "historic-climate.nc")
    ]

    for src, dst_name in mappings:
        # Determine if source is directory for recursive copy
        is_dir = src.endswith("ch4_input")
        
        if dst_name == ".":
            dst_path = target_dir
        else:
            dst_path = os.path.join(target_dir, dst_name)
            
        print(f"\nCopying {src} -> {dst_path}")
        
        cmd = ["gsutil", "-m", "cp"]
        if is_dir:
            cmd.append("-r")
            
        cmd.extend([src, dst_path])
        
        print(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"Successfully copied {src}")
        except subprocess.CalledProcessError as e:
            print(f"Error copying {src}: {e}")
            sys.exit(1)

    print("\nAll files copied successfully.")

if __name__ == "__main__":
    main()
