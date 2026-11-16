#!/usr/bin/env python3
"""
Analyze PF-AK v0.1 dataset structure and data availability

Inspects the Wang et al. (2018) Alaska permafrost synthesis dataset to:
- List all stations and their metadata
- Check data completeness for each variable
- Identify prototype stations for benchmarking
- Extract station-specific data

Usage:
    python3 analyze_pfak.py --data PF_AK_v0.1_b4e8.csv
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path

def load_pfak_data(filepath):
    """Load PF-AK dataset."""
    print(f"Loading PF-AK data from {filepath}")
    df = pd.read_csv(filepath)
    
    # Replace missing value codes with NaN
    df = df.replace(-999.99, np.nan)
    
    print(f"  Loaded {len(df)} rows")
    print(f"  Columns: {', '.join(df.columns)}")
    
    return df

def analyze_stations(df):
    """Analyze station metadata and data availability."""
    print("\n" + "=" * 80)
    print("Station Analysis")
    print("=" * 80)
    
    # Get unique stations
    stations = df[['Name', 'Code', 'Lat', 'Lon']].drop_duplicates().sort_values('Name')
    
    print(f"\nTotal stations: {len(stations)}")
    print("\nStation list:")
    print(stations.to_string(index=False))
    
    return stations

def analyze_data_completeness(df):
    """Analyze data completeness by station and variable."""
    print("\n" + "=" * 80)
    print("Data Completeness Analysis")
    print("=" * 80)
    
    variables = ['Snod', 'Tair', 'Ts25cm', 'Ts50cm', 'Ts75cm', 'Ts100cm', 'Tsur', 'VWC_top']
    
    completeness = []
    
    for station in df['Name'].unique():
        station_data = df[df['Name'] == station]
        total_months = len(station_data)
        
        row = {'Station': station, 'Total_Months': total_months}
        
        for var in variables:
            n_valid = station_data[var].notna().sum()
            pct_complete = (n_valid / total_months * 100) if total_months > 0 else 0
            row[f'{var}_n'] = n_valid
            row[f'{var}_pct'] = pct_complete
        
        completeness.append(row)
    
    comp_df = pd.DataFrame(completeness)
    
    print("\nData completeness by station (first 10):")
    print(comp_df.head(10).to_string(index=False))
    
    return comp_df

def analyze_prototype_stations(df, station_names):
    """Detailed analysis of prototype stations."""
    print("\n" + "=" * 80)
    print("Prototype Station Analysis")
    print("=" * 80)
    
    for station_name in station_names:
        print(f"\n{'-' * 80}")
        print(f"Station: {station_name}")
        print(f"{'-' * 80}")
        
        station_data = df[df['Name'] == station_name].copy()
        
        if len(station_data) == 0:
            print(f"  ✗ No data found for {station_name}")
            continue
        
        # Metadata
        meta = station_data.iloc[0]
        print(f"  Code: {meta['Code']}")
        print(f"  Location: {meta['Lat']:.4f}°N, {meta['Lon']:.4f}°W")
        
        # Time range
        years = station_data['Year'].unique()
        print(f"  Years: {min(years)}-{max(years)} ({len(years)} years)")
        print(f"  Total months: {len(station_data)}")
        
        # Data availability
        print(f"\n  Variable availability:")
        variables = ['Tair', 'Snod', 'Ts25cm', 'Ts50cm', 'Ts75cm', 'Ts100cm', 'Tsur', 'VWC_top']
        
        for var in variables:
            n_valid = station_data[var].notna().sum()
            pct = (n_valid / len(station_data) * 100)
            status = "✓" if pct > 50 else "⚬" if pct > 0 else "✗"
            print(f"    {status} {var:10s}: {n_valid:4d}/{len(station_data):4d} ({pct:5.1f}%)")
        
        # Summary statistics for key variables
        print(f"\n  Temperature statistics (°C):")
        if station_data['Tair'].notna().sum() > 0:
            print(f"    Air temp:     {station_data['Tair'].mean():6.2f} ± {station_data['Tair'].std():5.2f}")
        if station_data['Ts25cm'].notna().sum() > 0:
            print(f"    Ground 25cm:  {station_data['Ts25cm'].mean():6.2f} ± {station_data['Ts25cm'].std():5.2f}")
        if station_data['Ts50cm'].notna().sum() > 0:
            print(f"    Ground 50cm:  {station_data['Ts50cm'].mean():6.2f} ± {station_data['Ts50cm'].std():5.2f}")

def extract_station_data(df, station_name, output_dir):
    """Extract and save data for a single station."""
    station_data = df[df['Name'] == station_name].copy()
    
    if len(station_data) == 0:
        print(f"  ✗ No data for {station_name}")
        return None
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean station name for filename
    clean_name = station_name.lower().replace(' ', '_')
    output_file = output_dir / f"pfak_{clean_name}.csv"
    
    station_data.to_csv(output_file, index=False)
    print(f"  ✓ Saved: {output_file}")
    
    return output_file

def main():
    parser = argparse.ArgumentParser(
        description="Analyze PF-AK v0.1 dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--data',
        type=str,
        default='PF_AK_v0.1_b4e8.csv',
        help='PF-AK data file'
    )
    parser.add_argument(
        '--extract',
        nargs='+',
        help='Extract data for specified stations'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./extracted',
        help='Output directory for extracted station data'
    )
    
    args = parser.parse_args()
    
    # Load data
    df = load_pfak_data(args.data)
    
    # Analyze stations
    stations = analyze_stations(df)
    
    # Analyze data completeness
    completeness = analyze_data_completeness(df)
    
    # Analyze prototype stations
    prototype_stations = ['Deadhorse', 'Imnaviat', 'Smith Lake 1']
    analyze_prototype_stations(df, prototype_stations)
    
    # Extract station data if requested
    if args.extract:
        print("\n" + "=" * 80)
        print("Extracting Station Data")
        print("=" * 80)
        for station in args.extract:
            print(f"\nExtracting {station}...")
            extract_station_data(df, station, args.output_dir)
    
    print("\n" + "=" * 80)
    print("Analysis Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
