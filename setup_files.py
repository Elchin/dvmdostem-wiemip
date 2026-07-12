#!/usr/bin/env python3
import os
import subprocess
import argparse
import sys
import csv
import shutil

def load_cases_from_csv(csv_path):
    cases = {}
    with open(csv_path, mode='r', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        # headers: Simulation, run-mask.nc, historic-climate.nc, etc.
        dest_names = headers[1:]
        
        for row in reader:
            if not row:
                continue
            sim_name = row[0]
            mappings = []
            for i, src in enumerate(row[1:]):
                dest = dest_names[i]
                mappings.append((src, dest))
            cases[sim_name] = mappings
    return cases

def main():
    parser = argparse.ArgumentParser(description="Setup experiment files from GCS.")
    parser.add_argument(
        "--dest-folder",
        type=str,
        default="/mnt/exacloud/ext_ejafarov_woodwellclimate_org",
        help="Base destination folder where the experiment folder will be created."
    )
    # Hardcode the CSV file path
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "WIEMIP_SimulationInputFiles.csv")
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
        
    try:
        cases = load_cases_from_csv(csv_path)
    except Exception as e:
        print(f"Error loading cases from CSV: {e}")
        sys.exit(1)
        
    available_cases = ", ".join(cases.keys())
    
    # Add the simulation argument now that we have the choices
    parser.add_argument(
        "--simulation",
        type=str,
        default="Special_spin_WetlandON" if "Special_spin_WetlandON" in cases else list(cases.keys())[0],
        choices=list(cases.keys()),
        help=f"Target simulation case to create inside the destination folder. Available cases: {available_cases}"
    )
    
    # Re-parse to get the simulation argument
    args, unknown = parser.parse_known_args()
    
    # If the user passes something like --Exp_spin_noFire, we can treat it as the simulation name.
    for arg in unknown:
        if arg.startswith("--") and len(arg) > 2:
            potential_case = arg[2:]
            if potential_case in cases:
                args.simulation = potential_case
            break

    base_dir = args.dest_folder
    target_dir = os.path.join(base_dir, args.simulation)

    print(f"Creating target directory: {target_dir}")
    os.makedirs(target_dir, exist_ok=True)

    if args.simulation not in cases:
        print(f"Error: Unknown case '{args.simulation}'. Available cases are: {available_cases}")
        sys.exit(1)

    mappings = cases[args.simulation]
    
    # Check for missing files before starting copies
    for src, dst_name in mappings:
        if src in ["NA", "?????"]:
            print(f"Error: Source file for '{dst_name}' is missing ('{src}') in case '{args.simulation}'.")
            sys.exit(1)

    is_const_sim = False

    for src, dst_name in mappings:
        if dst_name == "co2.nc" and src.endswith("co2_cnst.nc"):
            is_const_sim = True
            
        if dst_name == ".":
            dst_path = target_dir
        else:
            dst_path = os.path.join(target_dir, dst_name)
            
        print(f"\nCopying {src} -> {dst_path}")
        
        cmd = ["gsutil", "-m", "cp", src, dst_path]
        
        print(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"Successfully copied {src}")
        except subprocess.CalledProcessError as e:
            print(f"Error copying {src}: {e}")
            sys.exit(1)

    print("\nAll files copied successfully.")

    if is_const_sim:
        print("\nConstant simulation detected. Generating ch4.nc from co2.nc...")
        try:
            src_nc = os.path.join(target_dir, "co2.nc")
            dst_nc = os.path.join(target_dir, "ch4.nc")
            
            # If a ch4.nc was downloaded from the CSV, this will overwrite it,
            # which is what we want to ensure the dimensions match perfectly.
            shutil.copy2(src_nc, dst_nc)
            
            import netCDF4 as nc
            ds = nc.Dataset(dst_nc, "r+")
            
            ds.renameVariable('co2', 'ch4')
            ch4_var = ds.variables['ch4']
            
            if hasattr(ch4_var, 'standard_name'):
                ch4_var.standard_name = ch4_var.standard_name.replace('CO2', 'CH4')
                
            data = ch4_var[:]
            # Replace the constant CO2 value (280.0) with the constant CH4 value (1015.0)
            data[data == 280.0] = 1015.0
            ch4_var[:] = data
            
            ds.close()
            print("Successfully created ch4.nc with values updated from 280 to 1015.")
        except Exception as e:
            print(f"Error creating ch4.nc: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
