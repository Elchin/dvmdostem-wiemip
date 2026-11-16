#!/usr/bin/env python3
"""
Download CRU-TS (CRU Time Series) data for DVM-DOS-TEM forcing

CRU-TS is a monthly gridded climate dataset from the Climatic Research Unit,
University of East Anglia. This script downloads CRU data at specific station
coordinates for use in DVM-DOS-TEM ground temperature benchmarking.

Requirements:
    pip install netCDF4 numpy requests xarray

Data Source: 
    https://crudata.uea.ac.uk/cru/data/hrg/
    CEDA Archive: https://data.ceda.ac.uk/badc/cru/data/cru_ts/
    
Citation:
    Harris, I., Osborn, T.J., Jones, P. et al. (2020). Version 4 of the CRU TS 
    monthly high-resolution gridded multivariate climate dataset. Sci Data 7, 109.
    https://doi.org/10.1038/s41597-020-0453-3
"""

import os
import sys
from pathlib import Path
import argparse
import numpy as np
try:
    import netCDF4 as nc
    import xarray as xr
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install netCDF4 xarray")
    sys.exit(1)

# CRU-TS version and base URL
CRU_VERSION = "4.07"  # Update to 4.08 when available
CRU_BASE_URL = "https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/cruts.2304241047.v4.07"

# Alternative: CEDA Archive (requires registration)
CEDA_BASE_URL = "https://data.ceda.ac.uk/badc/cru/data/cru_ts/cru_ts_4.07/data"

# CRU variable mappings
CRU_VARIABLES = {
    "tmp": {
        "long_name": "near-surface temperature",
        "file_pattern": "cru_ts4.07.1901.2022.tmp.dat.nc",
        "url_pattern": "tmp/cru_ts4.07.1901.2022.tmp.dat.nc.gz",
        "standard_name": "air_temperature",
        "units": "degrees_C"
    },
    "pre": {
        "long_name": "precipitation",
        "file_pattern": "cru_ts4.07.1901.2022.pre.dat.nc",
        "url_pattern": "pre/cru_ts4.07.1901.2022.pre.dat.nc.gz",
        "standard_name": "precipitation_amount",
        "units": "mm"
    },
    "vap": {
        "long_name": "vapor pressure",
        "file_pattern": "cru_ts4.07.1901.2022.vap.dat.nc",
        "url_pattern": "vap/cru_ts4.07.1901.2022.vap.dat.nc.gz",
        "standard_name": "water_vapor_pressure",
        "units": "hPa"
    },
    "cld": {
        "long_name": "cloud cover",
        "file_pattern": "cru_ts4.07.1901.2022.cld.dat.nc",
        "url_pattern": "cld/cru_ts4.07.1901.2022.cld.dat.nc.gz",
        "standard_name": "cloud_area_fraction",
        "units": "percentage"
    },
    "wet": {
        "long_name": "wet days",
        "file_pattern": "cru_ts4.07.1901.2022.wet.dat.nc",
        "url_pattern": "wet/cru_ts4.07.1901.2022.wet.dat.nc.gz",
        "standard_name": "number_of_days_with_lwe_thickness_of_precipitation_amount_above_threshold",
        "units": "days"
    }
}

# Prototype station coordinates
PROTOTYPE_STATIONS = {
    "Deadhorse": {
        "lat": 70.1997,
        "lon": -148.4597,
        "network": "GI-UAF",
        "description": "North Slope tundra, continuous permafrost"
    },
    "Toolik": {
        "lat": 68.6250,
        "lon": -149.5972,
        "network": "GI-UAF",
        "description": "Arctic foothills tundra"
    },
    "Smith_Lake": {
        "lat": 63.9897,
        "lon": -145.4019,
        "network": "GI-UAF",
        "description": "Interior Alaska, boreal forest, discontinuous permafrost"
    },
    "Healy": {
        "lat": 63.8761,
        "lon": -149.0933,
        "network": "GI-UAF",
        "description": "Interior Alaska, boreal forest"
    }
}

def print_download_instructions():
    """Print instructions for manual CRU download."""
    print("\n" + "=" * 80)
    print("CRU-TS Data Download Instructions")
    print("=" * 80)
    print("\nThe CRU-TS dataset files are large (~200-600 MB compressed per variable).")
    print("Manual download is recommended.")
    print("\n1. Download from CRU website:")
    print("   https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.07/")
    print("\n2. Or register and download from CEDA Archive:")
    print("   https://data.ceda.ac.uk/badc/cru/data/cru_ts/cru_ts_4.07/data/")
    print("\n3. Download these files:")
    for var, info in CRU_VARIABLES.items():
        print(f"   - {info['file_pattern']} ({info['long_name']})")
    print("\n4. Place downloaded files (decompressed) in:")
    print("   benchmarking/data/climate/CRU/")
    print("\n5. Then run this script with --local flag to extract station data")
    print("\nAlternatively, use wget to download (example):")
    print(f"  cd benchmarking/data/climate/CRU/")
    for var, info in CRU_VARIABLES.items():
        url = f"{CRU_BASE_URL}/{info['url_pattern']}"
        print(f"  wget {url}")
        print(f"  gunzip {info['file_pattern']}.gz")
    print("\n" + "=" * 80)

def extract_station_from_cru(cru_file, lat, lon, variable, station_name, dest_dir):
    """
    Extract time series at station location from CRU gridded file.
    
    Parameters
    ----------
    cru_file : Path
        Path to CRU NetCDF file
    lat : float
        Station latitude
    lon : float
        Station longitude
    variable : str
        CRU variable name (tmp, pre, vap, cld, wet)
    station_name : str
        Station name for output file
    dest_dir : Path
        Destination directory for extracted data
    """
    print(f"\nExtracting {variable} at {station_name} ({lat:.4f}°N, {lon:.4f}°E)")
    
    if not cru_file.exists():
        print(f"  ✗ Error: CRU file not found: {cru_file}")
        return None
    
    # Open CRU dataset
    try:
        ds = xr.open_dataset(cru_file)
    except Exception as e:
        print(f"  ✗ Error opening CRU file: {e}")
        return None
    
    # CRU uses 0-360 longitude convention
    if lon < 0:
        lon_360 = lon + 360
    else:
        lon_360 = lon
    
    print(f"  CRU file: {cru_file.name}")
    print(f"  Coordinates: {lat:.4f}°N, {lon_360:.4f}°E (0-360 convention)")
    
    # Find nearest grid cell
    try:
        # CRU uses 'lat' and 'lon' dimension names
        data_point = ds.sel(lat=lat, lon=lon_360, method='nearest')
        
        # Get actual grid cell coordinates
        grid_lat = float(data_point.lat.values)
        grid_lon = float(data_point.lon.values)
        
        print(f"  Nearest grid cell: {grid_lat:.2f}°N, {grid_lon:.2f}°E")
        print(f"  Distance: ~{np.sqrt((grid_lat-lat)**2 + (grid_lon-lon_360)**2)*111:.1f} km")
        
        # Extract time series
        var_name = list(ds.data_vars)[0]  # CRU files have single variable
        timeseries = data_point[var_name]
        
        # Get time range
        time_start = str(data_point.time.values[0])[:10]
        time_end = str(data_point.time.values[-1])[:10]
        print(f"  Time range: {time_start} to {time_end}")
        print(f"  Data points: {len(timeseries.time)}")
        
        # Check for missing data
        n_missing = np.isnan(timeseries.values).sum()
        if n_missing > 0:
            print(f"  ⚠ Warning: {n_missing} missing values ({n_missing/len(timeseries)*100:.1f}%)")
        
        # Save extracted data
        station_dir = dest_dir / station_name.lower().replace(" ", "_")
        station_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = station_dir / f"cru_ts_{variable}_{station_name.lower()}_{CRU_VERSION}.nc"
        
        # Create output dataset
        ds_out = xr.Dataset(
            {
                variable: (['time'], timeseries.values),
            },
            coords={
                'time': timeseries.time.values,
                'lat': grid_lat,
                'lon': grid_lon
            },
            attrs={
                'title': f'CRU-TS {variable} at {station_name}',
                'station_name': station_name,
                'station_lat': lat,
                'station_lon': lon,
                'grid_lat': grid_lat,
                'grid_lon': grid_lon,
                'source': f'CRU TS {CRU_VERSION}',
                'variable': variable,
                'long_name': CRU_VARIABLES[variable]['long_name'],
                'units': CRU_VARIABLES[variable]['units'],
                'extraction_date': str(np.datetime64('now'))
            }
        )
        
        ds_out.to_netcdf(output_file)
        print(f"  ✓ Saved: {output_file.name}")
        
        return output_file
        
    except Exception as e:
        print(f"  ✗ Error extracting data: {e}")
        return None
    finally:
        ds.close()

def process_station(station_name, station_info, cru_dir, dest_dir, variables):
    """
    Process all CRU variables for a single station.
    
    Parameters
    ----------
    station_name : str
        Station name
    station_info : dict
        Station metadata
    cru_dir : Path
        Directory containing CRU NetCDF files
    dest_dir : Path
        Destination directory for extracted data
    variables : list
        List of CRU variables to process
    """
    print("\n" + "=" * 80)
    print(f"Processing {station_name}")
    print("=" * 80)
    print(f"Location: {station_info['lat']:.4f}°N, {station_info['lon']:.4f}°E")
    print(f"Network: {station_info['network']}")
    print(f"Description: {station_info['description']}")
    
    results = {}
    
    for var in variables:
        if var not in CRU_VARIABLES:
            print(f"\n⚠ Warning: Unknown variable '{var}', skipping")
            continue
        
        # Find CRU file for this variable
        cru_file = cru_dir / CRU_VARIABLES[var]['file_pattern']
        
        if not cru_file.exists():
            # Try .gz version
            cru_file_gz = Path(str(cru_file) + ".gz")
            if cru_file_gz.exists():
                print(f"\n✗ Found compressed file: {cru_file_gz.name}")
                print(f"  Decompress with: gunzip {cru_file_gz}")
                results[var] = None
                continue
        
        result = extract_station_from_cru(
            cru_file,
            station_info['lat'],
            station_info['lon'],
            var,
            station_name,
            dest_dir
        )
        
        results[var] = result
    
    # Summary
    successful = sum(1 for r in results.values() if r is not None)
    print(f"\n{'=' * 80}")
    print(f"Station {station_name} summary: {successful}/{len(variables)} variables extracted")
    print("=" * 80)
    
    return results

def main():
    parser = argparse.ArgumentParser(
        description="Extract CRU-TS data at station locations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show download instructions
  python download_cru.py --instructions
  
  # Extract data for default stations (after manual CRU download)
  python download_cru.py --cru-dir ../../data/climate/CRU
  
  # Extract specific variables and stations
  python download_cru.py --cru-dir ../../data/climate/CRU \\
      --variables tmp pre vap --stations Deadhorse Toolik
        """
    )
    
    parser.add_argument(
        "--instructions",
        action="store_true",
        help="Print download instructions and exit"
    )
    parser.add_argument(
        "--cru-dir",
        type=str,
        default="../../data/climate/CRU",
        help="Directory containing CRU NetCDF files"
    )
    parser.add_argument(
        "--dest-dir",
        type=str,
        default="../../data/climate/CRU",
        help="Destination directory for extracted station data"
    )
    parser.add_argument(
        "--variables",
        nargs="+",
        default=["tmp", "pre", "vap", "cld"],
        help="CRU variables to extract (default: tmp pre vap cld)"
    )
    parser.add_argument(
        "--stations",
        nargs="+",
        default=["Deadhorse", "Toolik"],
        help="Station names to process (default: Deadhorse Toolik)"
    )
    
    args = parser.parse_args()
    
    # Print instructions if requested
    if args.instructions:
        print_download_instructions()
        sys.exit(0)
    
    cru_dir = Path(args.cru_dir)
    dest_dir = Path(args.dest_dir)
    
    print("\n" + "=" * 80)
    print(f"CRU-TS Data Extraction for Station Locations")
    print("=" * 80)
    print(f"CRU version: {CRU_VERSION}")
    print(f"CRU directory: {cru_dir.absolute()}")
    print(f"Output directory: {dest_dir.absolute()}")
    print(f"Variables: {', '.join(args.variables)}")
    print(f"Stations: {', '.join(args.stations)}")
    
    # Check if CRU directory exists
    if not cru_dir.exists():
        print(f"\n✗ Error: CRU directory not found: {cru_dir}")
        print("\nRun with --instructions flag to see download instructions")
        sys.exit(1)
    
    # Check for CRU files
    print("\nChecking for CRU files...")
    missing_files = []
    for var in args.variables:
        if var in CRU_VARIABLES:
            cru_file = cru_dir / CRU_VARIABLES[var]['file_pattern']
            if cru_file.exists():
                print(f"  ✓ Found: {cru_file.name}")
            else:
                print(f"  ✗ Missing: {cru_file.name}")
                missing_files.append(var)
    
    if missing_files:
        print(f"\n✗ Missing CRU files for variables: {', '.join(missing_files)}")
        print("\nRun with --instructions flag to see download instructions")
        sys.exit(1)
    
    # Process each station
    all_results = {}
    for station_name in args.stations:
        if station_name not in PROTOTYPE_STATIONS:
            print(f"\n⚠ Warning: Station '{station_name}' not found in prototype list")
            print(f"   Available: {', '.join(PROTOTYPE_STATIONS.keys())}")
            continue
        
        station_info = PROTOTYPE_STATIONS[station_name]
        results = process_station(
            station_name,
            station_info,
            cru_dir,
            dest_dir,
            args.variables
        )
        all_results[station_name] = results
    
    # Final summary
    print("\n" + "=" * 80)
    print("Overall Summary")
    print("=" * 80)
    for station_name, results in all_results.items():
        successful = sum(1 for r in results.values() if r is not None)
        print(f"{station_name}: {successful}/{len(results)} variables extracted")
    print("=" * 80)
    
    print("\nNext steps:")
    print("  1. Download station observations (PF-AK) if not already done")
    print("  2. Merge CRU + station data (scripts/prepare_inputs/merge_cru_station.py)")
    print("  3. Create DVM-DOS-TEM input files")

if __name__ == "__main__":
    main()
