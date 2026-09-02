#!/usr/bin/env python3
#
# setup_overshoot_sim_files.py
# Modified from setup_files.py by Elchin Javarov.
# Modified by: Joshua M. Rady
# Proj. 14 Exp. 1
# Woodwell Climate Research Center
# 8/29/2026
#
# This script downloads the input file for a specific WIEMIP overshoot simulation.
#
# Changes from setup_files.py:
# - Change the CSV that specifes the files.
# - Remove the is_const_sim block.  We provide a constant CH4 file for the overshoots.
# - Change from gsutil -m cp to gcloud storage cp.
# - Some columns are NA by design.  Turn error into informational warning.
# - Treat "Placeholder" values as missing.
# - Update default simulation.
# - Add nested 'config' and 'input' directories and organize the input files in them.
# - Print the files downloaded to a ReadMe file.
#___________________________________________________________________________________________________
import os
import subprocess
import argparse
import sys
import csv
from datetime import date

def load_cases_from_csv(csv_path):
    cases = {}
    with open(csv_path, mode='r', newline='') as f:
        reader = csv.reader(f)
        # Read the headers: Simulation, run-mask.nc, historic-climate.nc, etc.:
        headers = next(reader)
        # All but the first header field hold the standard DVM-DOS-TEM input file names for the
        # destination files:
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
        default=f"/mnt/exacloud/{os.environ.get('USER', 'ejafarov_woodwellclimate_org')}",
        help="Base destination folder where the experiment folder will be created."
    )
    # Hardcode the CSV file path
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "WEIMIP_Overshoot_SimulationInputs.csv")
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
        default="Special_spin_Wetland" if "Special_spin_Wetland" in cases else list(cases.keys())[0],
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
    os.makedirs(os.path.join(target_dir, "config"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "input"), exist_ok=True)

    if args.simulation not in cases:
        print(f"Error: Unknown case '{args.simulation}'. Available cases are: {available_cases}")
        sys.exit(1)

    mappings = cases[args.simulation]
    
    # Check for missing files before starting copies:
    for src, dst_name in mappings:
        if (src in ["?????"]) or ("Placeholder" in src):
            print(f"Error: Source file for '{dst_name}' is missing ('{src}') in case '{args.simulation}'.")
            print(f"Info: Source file for '{dst_name}' is missing ('{src}') in case '{args.simulation}'.")
            sys.exit(1)

    # Create a ReadMe file to document the files as we download them:
    with open(os.path.join(target_dir, "ReadMe.txt"), "w") as read_me_file:
        # Print the header:
        print("ReadMe_.txt", file=read_me_file)
        today = date.today()
        print(f"Created {today}", file=read_me_file)
        print("", file=read_me_file)
        print(f"    This directory contains files for the WIEMIP production run simulation {args.simulation}.", file=read_me_file)
        print("", file=read_me_file)
        print("The source of the input files:", file=read_me_file)

        # Download each available file:
        for src, dst_name in mappings:
            # Expect some files may be NA (e.g. historical forcings in a scenario run):
            if src in ["NA"]:
                print()
                print(f"Info: Source file for '{dst_name}' is not inculded in simulation '{args.simulation}'.")
                continue

            # Place the files it the traditional DVM-DOS-TEM simulation directory structure:
            if dst_name in ["config.js", "output_spec.csv"]:
                this_target_dir = os.path.join(target_dir, "config")
            else:
                this_target_dir = os.path.join(target_dir, "input")

            if dst_name == ".":
                dst_path = this_target_dir
            else:
                dst_path = os.path.join(this_target_dir, dst_name)
            
            copy_str = f"{src} -> {dst_path}"
            print(copy_str, file=read_me_file)
            print(f"\nCopying {copy_str}")
            
            cmd = ["gcloud", "storage", "cp", src, dst_path]
            
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
