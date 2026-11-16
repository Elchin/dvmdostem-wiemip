#!/usr/bin/env python3
"""
Download PF-AK v0.1 dataset from Arctic Data Center
DOI: https://doi.org/10.18739/A2KG55

This script downloads the Alaska Permafrost Synthesis dataset (Wang et al., 2018)
containing monthly ground temperature, soil moisture, and snow depth data from
72 monitoring stations (1997-2016).
"""

import os
import sys
import requests
import zipfile
from pathlib import Path

# Arctic Data Center package ID for PF-AK v0.1
PACKAGE_DOI = "doi:10.18739/A2KG55"
ARCTIC_DATA_CENTER_BASE = "https://arcticdata.io"

# Direct file URLs from Arctic Data Center
# These need to be updated with actual file identifiers from the dataset page
PFAK_FILES = {
    "monthly_data": "https://arcticdata.io/metacat/d1/mn/v2/object/...",  # Update with actual ID
    "metadata": "https://arcticdata.io/metacat/d1/mn/v2/object/...",      # Update with actual ID
}

def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    print(f"Downloading {url}")
    print(f"  -> {dest_path}")
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 8192
    downloaded = 0
    
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=block_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"  Progress: {progress:.1f}%", end='\r')
    
    print(f"\n  Downloaded: {dest_path.name} ({downloaded / 1e6:.2f} MB)")
    return dest_path

def download_pfak_dataset(dest_dir):
    """
    Download PF-AK v0.1 dataset.
    
    Parameters
    ----------
    dest_dir : Path or str
        Destination directory for downloaded files
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"PF-AK v0.1 Dataset Download")
    print(f"DOI: {PACKAGE_DOI}")
    print(f"Destination: {dest_dir}")
    print("-" * 60)
    
    # Manual download instructions
    print("\n" + "=" * 60)
    print("MANUAL DOWNLOAD REQUIRED")
    print("=" * 60)
    print("\nThe PF-AK v0.1 dataset must be downloaded manually from:")
    print(f"  https://arcticdata.io/catalog/view/{PACKAGE_DOI.replace('doi:', '')}")
    print("\nDownload the following files:")
    print("  1. Monthly ground temperature data (CSV or NetCDF)")
    print("  2. Station metadata file")
    print("  3. Data quality flags")
    print("\nPlace downloaded files in:")
    print(f"  {dest_dir.absolute()}")
    print("\nAlternatively, use the Arctic Data Center API or DataONE client.")
    print("=" * 60)
    
    # Create a README with instructions
    readme_path = dest_dir / "DOWNLOAD_INSTRUCTIONS.txt"
    with open(readme_path, 'w') as f:
        f.write("PF-AK v0.1 Dataset Download Instructions\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"DOI: {PACKAGE_DOI}\n")
        f.write(f"URL: https://arcticdata.io/catalog/view/{PACKAGE_DOI.replace('doi:', '')}\n\n")
        f.write("Required Files:\n")
        f.write("  1. Monthly ground temperature data\n")
        f.write("  2. Station metadata\n")
        f.write("  3. Soil moisture data (VWC)\n")
        f.write("  4. Snow depth data\n")
        f.write("  5. Air temperature data\n\n")
        f.write("Download Method 1: Web Interface\n")
        f.write("  - Visit the URL above\n")
        f.write("  - Download all data files\n")
        f.write(f"  - Save to: {dest_dir.absolute()}\n\n")
        f.write("Download Method 2: Using wget or curl\n")
        f.write("  - Get direct download URLs from the dataset page\n")
        f.write("  - Use wget or curl to download\n\n")
        f.write("Download Method 3: DataONE R client\n")
        f.write("  library(dataone)\n")
        f.write("  # Follow DataONE documentation\n")
    
    print(f"\nInstructions saved to: {readme_path}")
    
    return dest_dir

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download PF-AK v0.1 dataset from Arctic Data Center"
    )
    parser.add_argument(
        "--dest-dir",
        type=str,
        default="../data/observations/synthesis",
        help="Destination directory for downloaded files"
    )
    
    args = parser.parse_args()
    
    dest_dir = Path(args.dest_dir)
    download_pfak_dataset(dest_dir)
