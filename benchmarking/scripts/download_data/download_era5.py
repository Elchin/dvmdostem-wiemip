#!/usr/bin/env python3
"""
Download ERA5 reanalysis data from Copernicus Climate Data Store (CDS)

This script downloads ERA5 monthly data for specific station coordinates:
- Precipitation (total precipitation)
- Surface solar radiation downwards (SSRD)
- 2m dewpoint temperature (for vapor pressure calculation)

For Phase 1 prototype stations only.

Requirements:
    pip install cdsapi netCDF4 numpy

Setup:
    1. Register at https://cds.climate.copernicus.eu/
    2. Copy API key from https://cds.climate.copernicus.eu/api-how-to
    3. Create ~/.cdsapirc with:
       url: https://cds.climate.copernicus.eu/api/v2
       key: YOUR_UID:YOUR_API_KEY
"""

import os
import sys
from pathlib import Path
import numpy as np

# Station coordinates for Phase 1 prototype
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

# ERA5 variables to download
ERA5_VARIABLES = {
    "total_precipitation": "tp",           # m
    "surface_solar_radiation_downwards": "ssrd",  # J/m²
    "2m_dewpoint_temperature": "d2m",      # K
    "2m_temperature": "t2m",               # K (for validation/gap-filling)
    "surface_pressure": "sp"               # Pa (for vapor pressure calculation)
}

def check_cdsapi_setup():
    """Check if CDS API is properly configured."""
    cdsapirc = Path.home() / ".cdsapirc"
    
    if not cdsapirc.exists():
        print("\n" + "=" * 70)
        print("ERROR: CDS API not configured")
        print("=" * 70)
        print("\nTo download ERA5 data, you need to:")
        print("1. Register at https://cds.climate.copernicus.eu/")
        print("2. Get your API key from https://cds.climate.copernicus.eu/api-how-to")
        print("3. Create ~/.cdsapirc with:")
        print("   url: https://cds.climate.copernicus.eu/api/v2")
        print("   key: YOUR_UID:YOUR_API_KEY")
        print("\n4. Install cdsapi: pip install cdsapi")
        print("=" * 70)
        return False
    
    try:
        import cdsapi
        return True
    except ImportError:
        print("\n" + "=" * 70)
        print("ERROR: cdsapi not installed")
        print("=" * 70)
        print("\nInstall with: pip install cdsapi")
        print("=" * 70)
        return False

def download_era5_for_station(station_name, station_info, dest_dir, 
                                start_year=1997, end_year=2016):
    """
    Download ERA5 data for a specific station location.
    
    Parameters
    ----------
    station_name : str
        Station name
    station_info : dict
        Station metadata (lat, lon, etc.)
    dest_dir : Path
        Destination directory
    start_year : int
        Start year (default 1997)
    end_year : int
        End year (default 2016)
    """
    import cdsapi
    
    lat = station_info["lat"]
    lon = station_info["lon"]
    
    # Ensure longitude is in 0-360 range for ERA5
    if lon < 0:
        lon_360 = lon + 360
    else:
        lon_360 = lon
    
    print(f"\n{'=' * 70}")
    print(f"Downloading ERA5 data for {station_name}")
    print(f"{'=' * 70}")
    print(f"Location: {lat:.4f}°N, {lon:.4f}°E")
    print(f"Period: {start_year}-{end_year}")
    print(f"Network: {station_info['network']}")
    print(f"Description: {station_info['description']}")
    
    # Create station-specific directory
    station_dir = dest_dir / station_name.lower().replace(" ", "_")
    station_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize CDS API client
    c = cdsapi.Client()
    
    # Define area around station (±0.5 degrees for better spatial coverage)
    area = [lat + 0.5, lon_360 - 0.5, lat - 0.5, lon_360 + 0.5]  # N, W, S, E
    
    # Download monthly data
    output_file = station_dir / f"era5_monthly_{station_name.lower()}_{start_year}_{end_year}.nc"
    
    print(f"\nDownloading to: {output_file}")
    print("Variables: precipitation, solar radiation, dewpoint, temperature, pressure")
    print("This may take several minutes...")
    
    try:
        c.retrieve(
            'reanalysis-era5-single-levels-monthly-means',
            {
                'product_type': 'monthly_averaged_reanalysis',
                'variable': [
                    'total_precipitation',
                    'surface_solar_radiation_downwards',
                    '2m_dewpoint_temperature',
                    '2m_temperature',
                    'surface_pressure',
                ],
                'year': [str(year) for year in range(start_year, end_year + 1)],
                'month': [f'{m:02d}' for m in range(1, 13)],
                'time': '00:00',
                'area': area,
                'format': 'netcdf',
            },
            str(output_file)
        )
        
        print(f"\n✓ Successfully downloaded: {output_file.name}")
        print(f"  Size: {output_file.stat().st_size / 1e6:.2f} MB")
        
        # Save metadata
        metadata_file = station_dir / f"era5_metadata_{station_name.lower()}.txt"
        with open(metadata_file, 'w') as f:
            f.write(f"ERA5 Data for {station_name}\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Station: {station_name}\n")
            f.write(f"Latitude: {lat:.4f}°N\n")
            f.write(f"Longitude: {lon:.4f}°E\n")
            f.write(f"Network: {station_info['network']}\n")
            f.write(f"Description: {station_info['description']}\n\n")
            f.write(f"Period: {start_year}-{end_year}\n")
            f.write(f"Temporal resolution: Monthly means\n")
            f.write(f"Spatial area: {area[0]:.2f}°N to {area[2]:.2f}°N, ")
            f.write(f"{area[1]:.2f}°E to {area[3]:.2f}°E\n\n")
            f.write("Variables:\n")
            f.write("  - Total precipitation (tp) [m]\n")
            f.write("  - Surface solar radiation downwards (ssrd) [J/m²]\n")
            f.write("  - 2m dewpoint temperature (d2m) [K]\n")
            f.write("  - 2m temperature (t2m) [K]\n")
            f.write("  - Surface pressure (sp) [Pa]\n\n")
            f.write(f"Data file: {output_file.name}\n")
            f.write(f"Download date: {np.datetime64('now')}\n")
        
        print(f"✓ Metadata saved: {metadata_file.name}")
        
        return output_file
        
    except Exception as e:
        print(f"\n✗ Error downloading ERA5 data: {e}")
        print("\nPossible issues:")
        print("  - CDS API credentials not configured correctly")
        print("  - Network connection problems")
        print("  - CDS service temporarily unavailable")
        print("\nCheck https://cds.climate.copernicus.eu/ for service status")
        return None

def download_all_prototype_stations(dest_dir, stations=None, start_year=1997, end_year=2016):
    """
    Download ERA5 data for all (or selected) prototype stations.
    
    Parameters
    ----------
    dest_dir : Path or str
        Destination directory
    stations : list of str, optional
        List of station names to download. If None, download all.
    start_year : int
        Start year
    end_year : int
        End year
    """
    dest_dir = Path(dest_dir)
    
    if stations is None:
        stations = ["Deadhorse", "Toolik"]  # Default Phase 1 stations
    
    print("\n" + "=" * 70)
    print("ERA5 Data Download for Phase 1 Prototype Stations")
    print("=" * 70)
    print(f"Destination: {dest_dir.absolute()}")
    print(f"Stations: {', '.join(stations)}")
    print(f"Period: {start_year}-{end_year}")
    
    if not check_cdsapi_setup():
        sys.exit(1)
    
    successful = []
    failed = []
    
    for station_name in stations:
        if station_name not in PROTOTYPE_STATIONS:
            print(f"\n✗ Warning: Station '{station_name}' not found in prototype list")
            print(f"   Available stations: {', '.join(PROTOTYPE_STATIONS.keys())}")
            failed.append(station_name)
            continue
        
        station_info = PROTOTYPE_STATIONS[station_name]
        result = download_era5_for_station(
            station_name, station_info, dest_dir, start_year, end_year
        )
        
        if result:
            successful.append(station_name)
        else:
            failed.append(station_name)
    
    # Summary
    print("\n" + "=" * 70)
    print("Download Summary")
    print("=" * 70)
    print(f"Successful: {len(successful)}/{len(stations)}")
    if successful:
        print(f"  ✓ {', '.join(successful)}")
    if failed:
        print(f"Failed: {len(failed)}/{len(stations)}")
        print(f"  ✗ {', '.join(failed)}")
    print("=" * 70)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download ERA5 data for prototype stations"
    )
    parser.add_argument(
        "--dest-dir",
        type=str,
        default="../../data/climate/ERA5",
        help="Destination directory for ERA5 data"
    )
    parser.add_argument(
        "--stations",
        nargs="+",
        default=["Deadhorse", "Toolik"],
        help="Station names to download (default: Deadhorse Toolik)"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=1997,
        help="Start year (default: 1997)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2016,
        help="End year (default: 2016)"
    )
    
    args = parser.parse_args()
    
    download_all_prototype_stations(
        Path(args.dest_dir),
        args.stations,
        args.start_year,
        args.end_year
    )
