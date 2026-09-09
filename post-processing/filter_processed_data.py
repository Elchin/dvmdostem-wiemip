import os
import sys
import glob
import csv
import ast
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import gc

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)
from process_wiemip import plot_row, save_depth_climatology_figure, parse_config

def load_filters(csv_path):
    filters = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            var_name = row['var_name']
            try:
                # Parse the string "[min, max]" into a list
                range_wiemip = ast.literal_eval(row['range_WIEMIP'])
                filters[var_name] = (float(range_wiemip[0]), float(range_wiemip[1]))
            except (ValueError, SyntaxError) as e:
                print(f"Warning: Could not parse range for {var_name}: {row['range_WIEMIP']}")
    return filters

def process_directory(case_dir, filters_csv):
    if not os.path.isdir(case_dir):
        print(f"Error: Directory {case_dir} does not exist.")
        sys.exit(1)
        
    filters = load_filters(filters_csv)
    
    wiemip_output_dir = os.path.join(case_dir, 'wiemip_output')
    filtered_dir = os.path.join(case_dir, 'filtered')
    
    if not os.path.isdir(wiemip_output_dir):
        print(f"Error: wiemip_output directory not found in {case_dir}")
        sys.exit(1)
        
    os.makedirs(filtered_dir, exist_ok=True)
    
    veg_path = os.path.join(script_dir, 'wetland.nc')
    ds_veg = xr.open_dataset(veg_path).rename({'X': 'x', 'Y': 'y'})
    
    config = parse_config()
    time_aggregation = config.get('time_aggregation', {})
    
    nc_files = glob.glob(os.path.join(wiemip_output_dir, '*.nc'))
    if not nc_files:
        print(f"No .nc files found in {wiemip_output_dir}")
        return
        
    print(f"Processing {len(nc_files)} files in {wiemip_output_dir}...")
    
    for nc_file in nc_files:
        filename = os.path.basename(nc_file)
        
        # Determine variable name from filename
        # Format: <experiment_prefix>_<var_name>_<frequency>_05.nc
        # E.g., DVM-DOS-TEM_ctrl_alt_yr_05.nc
        
        # A simple way is to check which filter var_name is in the filename
        # But we need to be careful with overlapping names (e.g. cSoil and cSoilAbove1m)
        # Let's split by '_' and find the matching var_name
        parts = filename.replace('.nc', '').split('_')
        
        var_name = None
        # Usually the variable name is the 3rd or 4th part from the end
        # DVM-DOS-TEM_ctrl_alt_yr_05 -> alt is parts[-3]
        # DVM-DOS-TEM_ctrl_noFire_alt_yr_05 -> alt is parts[-3]
        if len(parts) >= 3:
            potential_var = parts[-3]
            if potential_var in filters:
                var_name = potential_var
                
        if not var_name:
            # Fallback: find the longest matching var_name in the filename
            for v in sorted(filters.keys(), key=len, reverse=True):
                if f"_{v}_" in filename:
                    var_name = v
                    break
                    
        if not var_name:
            print(f"  Skipping {filename}: Could not determine variable name or no filter defined.")
            continue
            
        min_val, max_val = filters[var_name]
        out_file = os.path.join(filtered_dir, filename)
        
        print(f"  Filtering {filename} (var: {var_name}, range: [{min_val}, {max_val}])...")
        
        try:
            with xr.open_dataset(nc_file) as ds:
                if var_name not in ds.variables:
                    print(f"    Warning: Variable {var_name} not found in dataset. Skipping.")
                    continue
                    
                print(f"    Filtering {filename} (this may take a moment for large files)...")
                
                da = ds[var_name]
                
                # Check if it's a massive variable (e.g., rhLayers which is 4D)
                if 'layer' in da.dims and 'time' in da.dims:
                    print(f"    Skipping massive variable {var_name} to prevent OOM kills.")
                    print(f"    Please filter this variable separately or on a machine with more memory.")
                    continue
                    
                time_len = da.sizes.get('time', 0)
                
                # Check if filtering is actually needed by checking min/max of the whole array
                # This is fast if the array fits in memory (which it does, since we skipped massive ones)
                orig_min = float(da.min().compute())
                orig_max = float(da.max().compute())
                
                needs_filtering = False
                if not np.isnan(orig_min) and not np.isnan(orig_max):
                    needs_filtering = (orig_min < min_val) or (orig_max > max_val)
                
                if time_len == 0:
                    data = da.values
                    mask = (data < min_val) | (data > max_val)
                    data[mask] = np.nan
                    
                    # Create a new dataset with the filtered data directly
                    ds_filtered = xr.Dataset(
                        {var_name: (da.dims, data, da.attrs)},
                        coords={c: ds.coords[c] for c in ds.coords},
                        attrs=ds.attrs
                    )
                    ds_filtered.to_netcdf(out_file, engine='netcdf4')
                    del data, mask, ds_filtered
                else:
                    # For time series, process chunk by chunk and concatenate
                    # We will use netCDF4 directly to avoid xarray's memory overhead during concatenation
                    import netCDF4 as nc
                    
                    # Create a template dataset with the first time step to set up the file structure
                    ds_template = ds.isel(time=slice(0, 1)).copy()
                    
                    # Filter the template
                    template_data = ds_template[var_name].values
                    mask = (template_data < min_val) | (template_data > max_val)
                    template_data[mask] = np.nan
                    ds_template[var_name].values = template_data
                    
                    # Save the template to create the file
                    # We need to make sure the time dimension is unlimited so we can append to it
                    ds_template.to_netcdf(out_file, engine='netcdf4', mode='w', unlimited_dims=['time'])
                    del ds_template, template_data, mask
                    
                    # Now append the rest of the chunks using netCDF4 library directly
                    chunk_size = 120
                    
                    with nc.Dataset(out_file, 'a') as dst:
                        var_dst = dst.variables[var_name]
                        
                        for t_start in range(1, time_len, chunk_size):
                            t_end = min(t_start + chunk_size, time_len)
                            
                            # Load chunk into memory as numpy array
                            chunk_data = da.isel(time=slice(t_start, t_end)).values
                            
                            # Apply filter using numpy
                            mask = (chunk_data < min_val) | (chunk_data > max_val)
                            chunk_data[mask] = np.nan
                            
                            # Write to the netCDF file
                            # To avoid the reshape error with netCDF4 when appending to an unlimited dimension,
                            # we can assign slice by slice if the chunk assignment fails, or we can use
                            # the following syntax which explicitly specifies all dimensions:
                            
                            if len(chunk_data.shape) == 3:
                                var_dst[t_start:t_end, :, :] = chunk_data
                            elif len(chunk_data.shape) == 4:
                                var_dst[t_start:t_end, :, :, :] = chunk_data
                            elif len(chunk_data.shape) == 2:
                                var_dst[t_start:t_end, :] = chunk_data
                            else:
                                var_dst[t_start:t_end] = chunk_data
                                
                            del chunk_data, mask
                            gc.collect()
                            
                if needs_filtering:
                    print(f"    Values out of bounds (min: {orig_min:.4g}, max: {orig_max:.4g}). Generating updated figure...")
                    
                    # Open the newly saved filtered file to plot it lazily
                    with xr.open_dataset(out_file) as ds_filtered_plot:
                        fig = plt.figure(figsize=(18, 10))
                        overall_shape = ds[var_name].shape
                        agg = time_aggregation.get(var_name, 'mean')
                        
                        fig.suptitle(f'Filtered Variable: {var_name} | Range: [{min_val}, {max_val}] | Shape: {overall_shape}', fontsize=16)
                        
                        units = ds[var_name].attrs.get('units', '')
                        
                        plot_row(fig, 0, var_name, ds, f'Original ({var_name})', agg, units, ds_veg)
                        plot_row(fig, 1, var_name, ds_filtered_plot, f'Filtered ({var_name})', agg, units, ds_veg)
                        
                        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
                        
                        fig_file = os.path.join(filtered_dir, f"{var_name}_summary.png")
                        plt.savefig(fig_file, dpi=150, bbox_inches='tight')
                        plt.close(fig)
                        print(f"    Saved figure to {fig_file}")
                        
                        if 'layer' in ds[var_name].dims:
                            save_depth_climatology_figure(var_name, ds_filtered_plot[var_name], filtered_dir, units)
                            
                gc.collect()
                
        except Exception as e:
            print(f"    Error processing {filename}: {e}")
            
    ds_veg.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python filter_processed_data.py <path_to_processed_case_directory>")
        print("Example: python filter_processed_data.py /mnt/disks/wiemip-data/processed/DVM-DOS-TEM_ctrl")
        sys.exit(1)
        
    case_directory = sys.argv[1]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filters_csv_path = os.path.join(script_dir, 'output_filters.csv')
    
    if not os.path.exists(filters_csv_path):
        print(f"Error: {filters_csv_path} not found.")
        sys.exit(1)
        
    process_directory(case_directory, filters_csv_path)
    print("Done.")