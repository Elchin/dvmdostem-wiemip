#!/usr/bin/env python3
import os
import subprocess
import argparse
import sys
import shutil
import netCDF4 as nc

CASES = {
    "Special_spin_WetlandON": [
        ("gs://wiemip/teminputs/co2_cnst.nc", "co2.nc"),
        ("gs://wiemip/teminputs/drainage_stable.nc", "drainage.nc"),
        ("gs://wiemip/teminputs/explicit-fire_stable.nc", "historic-explicit-fire.nc"),
        ("gs://wiemip/teminputs/fri-fire_stable.nc", "fri-fire.nc"),
        ("gs://wiemip/teminputs/new/run-mask2.nc", "run-mask.nc"),
        ("gs://wiemip/teminputs/new/texture.nc", "soil-texture.nc"),
        ("gs://wiemip/teminputs/new/topo.nc", "topo.nc"),
        ("gs://wiemip/teminputs/new/wetland.nc", "vegetation.nc"),
        #("gs://wiemip/teminputs/new/ch4_inputs", "."),
        ("gs://wiemip/spinup_noFire_noWetland/climate_stable_150yr.nc", "historic-climate.nc")
    ]
    # Add more cases here in the future
}

def main():
    parser = argparse.ArgumentParser(description="Setup experiment files from GCS.")
    parser.add_argument(
        "--dest-folder",
        type=str,
        default="/mnt/exacloud/ext_ejafarov_woodwellclimate_org",
        help="Base destination folder where the experiment folder will be created."
    )
    
    available_cases = ", ".join(CASES.keys())
    parser.add_argument(
        "--folder",
        type=str,
        default="Special_spin_WetlandON",
        choices=list(CASES.keys()),
        help=f"Target folder name to create inside the destination folder. Available cases: {available_cases}"
    )
    
    # Check if a positional or specific flag like --Exp_spin_noFire was passed
    # as a shorthand.
    args, unknown = parser.parse_known_args()
    
    # If the user passes something like --Exp_spin_noFire, we can treat it as the folder name.
    for arg in unknown:
        if arg.startswith("--") and len(arg) > 2:
            potential_case = arg[2:]
            if potential_case in CASES:
                args.folder = potential_case
            break

    base_dir = args.dest_folder
    target_dir = os.path.join(base_dir, args.folder)

    print(f"Creating target directory: {target_dir}")
    os.makedirs(target_dir, exist_ok=True)

    if args.folder not in CASES:
        print(f"Error: Unknown case '{args.folder}'. Available cases are: {available_cases}")
        sys.exit(1)

    mappings = CASES[args.folder]

    for src, dst_name in mappings:
        # Determine if source is directory for recursive copy
        is_dir = src.endswith("ch4_inputs")
        
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

    if args.folder == "Special_spin_WetlandON":
        print("\nCreating ch4.nc based on co2.nc...")
        try:
            src_nc = os.path.join(target_dir, "co2.nc")
            dst_nc = os.path.join(target_dir, "ch4.nc")
            
            shutil.copy2(src_nc, dst_nc)
            ds = nc.Dataset(dst_nc, "r+")
            
            ds.renameVariable('co2', 'ch4')
            ch4_var = ds.variables['ch4']
            
            if hasattr(ch4_var, 'standard_name'):
                ch4_var.standard_name = ch4_var.standard_name.replace('CO2', 'CH4')
                
            data = ch4_var[:]
            data[data == 280.0] = 1015.0
            ch4_var[:] = data
            
            ds.close()
            print("Successfully created ch4.nc with values updated from 280 to 1015.")
        except Exception as e:
            print(f"Error creating ch4.nc: {e}")

if __name__ == "__main__":
    main()
