import os
import glob
import csv
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# Force xarray to keep data on disk when doing large reductions
xr.set_options(keep_attrs=True)

# Configuration
CONFIG_SH_PATH = os.path.expanduser('~/dvmdostem-wiemip/post-processing/config.sh')
CSV_PATH = os.path.expanduser('~/dvmdostem-wiemip/post-processing/output_conversion_table.csv')
VEG_PATH = os.path.expanduser('~/dvmdostem-wiemip/post-processing/vegetation1_stable.nc')

OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/mnt/disks/wiemip-data/output')
LOCAL_BASE_RUN = os.path.join(OUTPUT_DIR, 'base_run')
LOCAL_WET_RUN = os.path.join(OUTPUT_DIR, 'wet_run')
LOCAL_WIEMIP_OUTPUT = os.path.join(OUTPUT_DIR, 'wiemip_output')
FIGURES_DIR = os.path.join(OUTPUT_DIR, 'figures')

os.makedirs(LOCAL_WIEMIP_OUTPUT, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

# Parse VAR_NAMES and aggregations from config.sh
var_names = []
time_aggregation = {}
gcm_pattern = "GCM"
experiment = "EXP"
with open(CONFIG_SH_PATH, 'r') as f:
    for line in f:
        line = line.strip()
        if line.startswith('VAR_NAMES='):
            content = line.split('=')[1].strip('()\'"')
            var_names = content.split()
        elif line.startswith('export AGG_'):
            parts = line.split('=')
            var_part = parts[0].replace('export AGG_', '')
            val_part = parts[1].strip('\'"')
            time_aggregation[var_part] = val_part
        elif line.startswith('export GCM_PATTERN='):
            gcm_pattern = line.split('=')[1].strip('\'"')
        elif line.startswith('export EXPERIMENT='):
            experiment = line.split('=')[1].strip('\'"')

# Parse CSV
var_config = {}
with open(CSV_PATH, 'r') as f:
    reader = csv.reader(f)
    next(reader) # header 1
    next(reader) # header 2
    for row in reader:
        if len(row) > 14:
            tem_name = row[4].strip()
            if tem_name in var_names:
                var_config[tem_name] = {
                    'trendy_name': row[2].strip(),
                    'wiemip_units': row[3].strip(),
                    'unit_conversion': row[9].strip(),
                    'merge': row[14].strip() == '1'
                }

# Load vegetation data
ds_veg = xr.open_dataset(VEG_PATH).rename({'X': 'x', 'Y': 'y'})
veg_cov = ds_veg['veg_pct_cov'].drop_vars(['x', 'y'], errors='ignore')

def apply_unit_conversion(da, conversion_type):
    if conversion_type == 'g -> kg':
        return (da * 0.001).astype(np.float32)
    elif conversion_type == 'mm -> kg, day -> s':
        return (da / 86400.0).astype(np.float32)
    elif conversion_type == 'g -> kg, mo -> s':
        days_in_month = da.time.dt.days_in_month
        return (da * 0.001 / (days_in_month * 86400.0)).astype(np.float32)
    elif conversion_type == 'C -> K':
        return (da + 273.15).astype(np.float32)
    return da

def plot_row(fig, row_idx, var_name, ds, title_prefix, agg_type, units):
    if ds is None or var_name not in ds:
        for col_idx in range(3):
            ax = fig.add_subplot(3, 3, row_idx * 3 + col_idx + 1)
            ax.axis('off')
            ax.text(0.5, 0.5, 'Data unavailable', ha='center', va='center')
        return

    da = ds[var_name]
    
    # "for GPP (time,pft,y,x), sum all pfts per month and then plot."
    if 'pft' in da.dims:
        time_len = len(da.time) if 'time' in da.dims else 0
        if time_len > 151:
            first_year = da.isel(time=slice(0, 12))
            last_year = da.isel(time=slice(-12, None))
            if agg_type == 'sum':
                da_first_map = first_year.sum(dim=['time', 'pft'], skipna=True, min_count=1).compute()
                da_last_map = last_year.sum(dim=['time', 'pft'], skipna=True, min_count=1).compute()
            else:
                da_first_map = first_year.mean(dim='time', skipna=True).sum(dim='pft', skipna=True, min_count=1).compute()
                da_last_map = last_year.mean(dim='time', skipna=True).sum(dim='pft', skipna=True, min_count=1).compute()
        elif time_len > 0:
            da_first_map = da.isel(time=0).sum(dim='pft', skipna=True, min_count=1).compute()
            da_last_map = da.isel(time=-1).sum(dim='pft', skipna=True, min_count=1).compute()
        else:
            da_first_map = da.sum(dim='pft', skipna=True, min_count=1).compute()
            da_last_map = da_first_map

        # For the timeseries, we need the spatial mean across x and y. 
        # Calculate spatial mean first (collapsing x,y) to massively reduce size, then sum PFTs
        da_ts = da.mean(dim=['x', 'y'], skipna=True).sum(dim='pft', skipna=True, min_count=1).compute()
        
    elif 'layer' in da.dims:
        time_len = len(da.time) if 'time' in da.dims else 0
        if time_len > 151:
            first_year = da.isel(time=slice(0, 12), layer=0)
            last_year = da.isel(time=slice(-12, None), layer=-1)
            if agg_type == 'sum':
                da_first_map = first_year.sum(dim='time', skipna=True, min_count=1).compute()
                da_last_map = last_year.sum(dim='time', skipna=True, min_count=1).compute()
            else:
                da_first_map = first_year.mean(dim='time', skipna=True).compute()
                da_last_map = last_year.mean(dim='time', skipna=True).compute()
        elif time_len > 0:
            da_first_map = da.isel(time=0, layer=0).compute()
            da_last_map = da.isel(time=-1, layer=-1).compute()
        else:
            da_first_map = da.isel(layer=0).compute()
            da_last_map = da.isel(layer=-1).compute()
            
        print(f"    Memory-optimized layer timeseries aggregation...")
        # Average over depth 0 and depth N, and spatial x/y
        da_ts_0 = da.isel(layer=0).mean(dim=['x', 'y'], skipna=True).compute()
        da_ts_N = da.isel(layer=-1).mean(dim=['x', 'y'], skipna=True).compute()
        da_ts = (da_ts_0 + da_ts_N) / 2.0

    else:
        time_len = len(da.time) if 'time' in da.dims else 0
        if time_len > 151:
            first_year = da.isel(time=slice(0, 12))
            last_year = da.isel(time=slice(-12, None))
            if agg_type == 'sum':
                da_first_map = first_year.sum(dim='time', skipna=True, min_count=1).compute()
                da_last_map = last_year.sum(dim='time', skipna=True, min_count=1).compute()
            else:
                da_first_map = first_year.mean(dim='time', skipna=True).compute()
                da_last_map = last_year.mean(dim='time', skipna=True).compute()
        elif time_len > 0:
            da_first_map = da.isel(time=0).compute()
            da_last_map = da.isel(time=-1).compute()
        else:
            da_first_map = da
            da_last_map = da
            
        da_ts = da.mean(dim=['x', 'y'], skipna=True).compute()
        
    shape_str = str(da.shape)
    
    if time_len > 0:
        
        t0 = da.time[0].dt
        t1 = da.time[-1].dt
        
        if time_len > 151:
            title0 = f"{title_prefix}\nYear {t0.year.item()} (Annual {agg_type.capitalize()})"
            title1 = f"{title_prefix}\nYear {t1.year.item()} (Annual {agg_type.capitalize()})"
        else:
            title0 = f"{title_prefix}\nYear {t0.year.item()}"
            title1 = f"{title_prefix}\nYear {t1.year.item()}"
            
        if 'layer' in da.dims:
            title0 += " (Layer 0)"
            title1 += f" (Layer {len(da.layer)-1})"
    else:
        da_first_map = da
        da_last_map = da
        title0 = f"{title_prefix} - No time data"
        title1 = f"{title_prefix} - No time data"
    
    # Subplot 1: Map of first year
    if time_len > 0 and da_first_map.ndim == 2:
        ax1 = fig.add_subplot(3, 3, row_idx * 3 + 1, projection=ccrs.NorthPolarStereo())
        ax1.set_extent([-180, 180, 45, 90], ccrs.PlateCarree())
        da_first_map = da_first_map.assign_coords(lat=ds_veg.lat, lon=ds_veg.lon)
        im1 = da_first_map.plot.pcolormesh(ax=ax1, x='lon', y='lat', transform=ccrs.PlateCarree(), add_colorbar=False)
        ax1.coastlines()
        plt.colorbar(im1, ax=ax1, orientation='horizontal', pad=0.15)
        ax1.set_title(f'{title0}\nMin:{float(da_first_map.min()):.2g} Max:{float(da_first_map.max()):.2g}')
    else:
        ax1 = fig.add_subplot(3, 3, row_idx * 3 + 1)
        if time_len > 0:
            da_first_map.plot(ax=ax1)
            ax1.set_title(f'{title0}\nMin:{float(da_first_map.min()):.2g} Max:{float(da_first_map.max()):.2g}')
        else:
            ax1.text(0.5, 0.5, 'No time data', ha='center', va='center')

    # Subplot 2: Map of last year
    if time_len > 0 and da_last_map.ndim == 2:
        ax2 = fig.add_subplot(3, 3, row_idx * 3 + 2, projection=ccrs.NorthPolarStereo())
        ax2.set_extent([-180, 180, 45, 90], ccrs.PlateCarree())
        da_last_map = da_last_map.assign_coords(lat=ds_veg.lat, lon=ds_veg.lon)
        im2 = da_last_map.plot.pcolormesh(ax=ax2, x='lon', y='lat', transform=ccrs.PlateCarree(), add_colorbar=False)
        ax2.coastlines()
        plt.colorbar(im2, ax=ax2, orientation='horizontal', pad=0.15)
        ax2.set_title(f'{title1}\nMean:{float(da_last_map.mean()):.2g}')
    else:
        ax2 = fig.add_subplot(3, 3, row_idx * 3 + 2)
        if time_len > 0:
            da_last_map.plot(ax=ax2)
            ax2.set_title(f'{title1}\nMean:{float(da_last_map.mean()):.2g}')
        else:
            ax2.text(0.5, 0.5, 'No time data', ha='center', va='center')
    
    # Subplot 3: Timeseries
    ax3 = fig.add_subplot(3, 3, row_idx * 3 + 3)
    
    # Plot using original time coordinates for true timeseries
    # If the time data is cftime, xarray handles it, but matplotlib might need help depending on version.
    # Usually da_ts.plot() handles cftime correctly.
    try:
        da_ts.plot(ax=ax3)
    except Exception as e:
        # Fallback to just values if dates cause issues
        ax3.plot(da_ts.values)
        ax3.set_xlabel('Time index')
        
    ts_title = f'{title_prefix} - Timeseries'
    if 'layer' in da.dims:
        ts_title += f'\n(Depth Avg [0] & [{len(da.layer)-1}])'
    ts_title += f'\nUnits: {units}'
    
    ax3.set_title(ts_title)
    ax3.set_ylabel(units)

for var in var_names:
    print(f"Processing {var}...")
    conf = var_config.get(var, {})
    trendy_name = conf.get('trendy_name', var.lower())
    merge = conf.get('merge', False)
    unit_conv = conf.get('unit_conversion', 'None')
    wiemip_units = conf.get('wiemip_units', '')
    agg = time_aggregation.get(var, 'mean')
    
    # Find files
    base_files = glob.glob(os.path.join(LOCAL_BASE_RUN, f"{var}_*tr*.nc"))
    wet_files = glob.glob(os.path.join(LOCAL_WET_RUN, f"{var}_*tr*.nc"))
    
    if not base_files:
        print(f"No base file found for {var}")
        continue
    
    # We only use ds_base to grab dimensions, not to read all data
    with xr.open_dataset(base_files[0]) as ds_base:
        dims = list(ds_base[var].dims)
        shape = ds_base[var].shape
        num_times = len(ds_base.time) if 'time' in dims else 1
    
    # Extract frequency from base filename (e.g. SWE_monthly_tr.nc)
    base_basename = os.path.basename(base_files[0])
    parts = base_basename.split('_')
    frequency = parts[1] if len(parts) > 1 else 'unknown'
    
    # Generate standard output filename
    nc_filename = f"DVMDOSTEM_{gcm_pattern}_{experiment}_{trendy_name}_{frequency}_noProcess_0.5deg.nc"
    out_file = os.path.join(LOCAL_WIEMIP_OUTPUT, nc_filename)
    
    if os.path.exists(out_file):
        os.remove(out_file)
        
    print(f"  Streaming to {out_file}...")
    
    do_merge = merge and bool(wet_files)
    
    if do_merge:
        # Load veg fraction once as a pure numpy array, float32
        veg_fraction_np = (veg_cov.values * 0.01).astype(np.float32)
        
    if 'time' in dims:
        import netCDF4 as nc
        import gc
        
        with nc.Dataset(out_file, 'w', format='NETCDF4') as nc_out:
            with nc.Dataset(base_files[0], 'r') as nc_base:
                for dim_name, dim in nc_base.dimensions.items():
                    nc_out.createDimension(dim_name, len(dim) if not dim.isunlimited() else None)
                    
                for v_name, v_in in nc_base.variables.items():
                    if v_name != var:
                        v_out = nc_out.createVariable(v_name, v_in.datatype, v_in.dimensions, zlib=True)
                        v_out.setncatts({k: v_in.getncattr(k) for k in v_in.ncattrs()})
                        v_out[:] = v_in[:]
                        
                v_base = nc_base.variables[var]
                
                # Check for _FillValue to apply during creation
                fill_val = None
                if hasattr(v_base, '_FillValue'):
                    fill_val = np.float32(v_base._FillValue)
                    
                v_out = nc_out.createVariable(trendy_name, np.float32, v_base.dimensions, zlib=True, chunksizes=v_base.chunking(), fill_value=fill_val)
                
                # Copy other attributes, omitting _FillValue since it's already handled
                atts = {}
                for k in v_base.ncattrs():
                    if k != '_FillValue':
                        val = v_base.getncattr(k)
                        if isinstance(val, (float, np.floating)):
                            val = np.float32(val)
                        atts[k] = val
                        
                v_out.setncatts(atts)
                v_out.units = wiemip_units
                
                nc_wet = nc.Dataset(wet_files[0], 'r') if do_merge else None
                v_wet = nc_wet.variables[var] if nc_wet else None
                
                # Determine optimal time chunk size based on input file chunking
                time_chunk = 12 # fallback to 1 year
                if isinstance(v_base.chunking(), list) or isinstance(v_base.chunking(), tuple):
                    time_chunk = v_base.chunking()[0]
                
                # Prevent massive memory usage if time_chunk is too huge (e.g. all times)
                # Max bytes we want to hold is ~4GB per array
                slice_bytes = np.prod(v_base.shape[1:]) * 4
                while time_chunk * slice_bytes > 4 * 1024**3 and time_chunk > 1:
                    time_chunk //= 2
                    
                print(f"      Optimized reading using time blocks of {time_chunk} steps...")
                
                for t_start in range(0, num_times, time_chunk):
                    t_end = min(t_start + time_chunk, num_times)
                    
                    import psutil
                    process = psutil.Process(os.getpid())
                    print(f"      Processing steps {t_start} to {t_end}... Mem: {process.memory_info().rss / 1024**3:.2f} GB")
                    
                    base_t = np.array(v_base[t_start:t_end, ...], dtype=np.float32)
                    
                    # Track missing values so we don't accidentally convert them during unit conversion
                    is_missing = None
                    if fill_val is not None:
                        is_missing = (base_t == fill_val)
                        
                    out_t = base_t.copy()
                    
                    if do_merge:
                        wet_t = np.array(v_wet[t_start:t_end, ...], dtype=np.float32)
                        
                        valid_t_len = wet_t.shape[0]
                        
                        # Find valid wet data (netcdf4 might return masked array or raw array with fill_val)
                        if fill_val is not None:
                            wet_valid = (wet_t != fill_val) & ~np.isnan(wet_t)
                        else:
                            wet_valid = ~np.isnan(wet_t)
                        
                        base_t_slice = base_t[:valid_t_len, ...]
                        out_t_slice = out_t[:valid_t_len, ...]
                        
                        merged_t = (base_t_slice * veg_fraction_np) + (wet_t * (1.0 - veg_fraction_np))
                        out_t_slice[wet_valid] = merged_t[wet_valid]
                        
                        del wet_t, wet_valid, merged_t, base_t_slice, out_t_slice
                        
                    if unit_conv == 'g -> kg':
                        out_t *= 0.001
                    elif unit_conv == 'mm -> kg, day -> s':
                        out_t /= 86400.0
                    elif unit_conv == 'g -> kg, mo -> s':
                        out_t *= (0.001 / (30.4 * 86400.0))
                    elif unit_conv == 'C -> K':
                        out_t += 273.15
                        
                    # Restore original fill values
                    if is_missing is not None:
                        out_t[is_missing] = fill_val
                        
                    v_out[t_start:t_end, ...] = out_t
                    del base_t, out_t, is_missing
                    
                    nc_out.sync()
                    gc.collect()
                        
                if nc_wet:
                    nc_wet.close()
    else:
        # For variables without time dimension, handle purely in memory
        ds_base = xr.open_dataset(base_files[0])
        base_slice = ds_base[var].compute()
        base_vals = base_slice.values.astype(np.float32)
        
        if do_merge:
            ds_wet = xr.open_dataset(wet_files[0])
            wet_slice = ds_wet[var].compute()
            wet_vals = wet_slice.values.astype(np.float32)
            has_wet = ~np.isnan(wet_vals)
            merged_vals = (base_vals * veg_fraction_np + wet_vals * (1.0 - veg_fraction_np)).astype(np.float32)
            out_vals = np.where(has_wet, merged_vals, base_vals).astype(np.float32)
            ds_wet.close()
        else:
            out_vals = base_vals
            
        da_out = base_slice.copy(data=out_vals)
        da_out = apply_unit_conversion(da_out, unit_conv)
        da_out.values = da_out.values.astype(np.float32)
        
        da_out.attrs['units'] = wiemip_units
        da_out.name = trendy_name
        ds_out = ds_base.copy()
        if trendy_name != var and var in ds_out:
            ds_out = ds_out.drop_vars(var)
        ds_out[trendy_name] = da_out
        ds_out.to_netcdf(out_file, engine='netcdf4')
        ds_base.close()
        ds_out.close()
        
    import gc
    gc.collect()
    
    # Plotting
    print("  Generating figure...")
    fig = plt.figure(figsize=(18, 15))
    
    # We reload the base and wet datasets explicitly for plotting here to avoid
    # keeping them in memory during the merge operation.
    ds_base_plot = xr.open_dataset(base_files[0])
    overall_shape = ds_base_plot[var].shape
    
    fig.suptitle(f'Variable: {var} -> {trendy_name} (Merge: {merge}) | Shape: {overall_shape}', fontsize=16)
    
    plot_row(fig, 0, var, ds_base_plot, f'Base Run ({var})', agg, ds_base_plot[var].attrs.get('units', ''))
    
    if wet_files:
        ds_wet_plot = xr.open_dataset(wet_files[0])
        plot_row(fig, 1, var, ds_wet_plot, f'Wet Run ({var})', agg, ds_wet_plot[var].attrs.get('units', ''))
    else:
        plot_row(fig, 1, var, None, f'Wet Run ({var})', agg, '')
        
        # Read back the saved output or plot directly from ds_out
    # Try Dask parallel graph explicitly 
    ds_out_saved = xr.open_dataset(out_file)
    
    # Just compute the spatial mean across x and y incrementally using loop to avoid massive mem spike
    # First, mean over x and y for timeseries
    plot_row(fig, 2, trendy_name, ds_out_saved, f'WIEMIP Output ({trendy_name})', agg, wiemip_units)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    fig_file = os.path.join(FIGURES_DIR, f"{var}_summary.png")
    plt.savefig(fig_file, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved figure to {fig_file}")
    
    # Extra figure for 4D layer datasets
    if 'layer' in ds_out_saved[trendy_name].dims:
        print(f"  Generating depth climatology figure for {var}...")
        fig_depth = plt.figure(figsize=(15, 6))
        fig_depth.suptitle(f'{trendy_name} - Depth Profile Climatology & Stats', fontsize=16)
        
        # Spatial mean of the full 4D dataset to get (time, layer)
        print(f"    Computing spatial mean for depth profiles (this may take a moment)...")
        da_out_spatial = ds_out_saved[trendy_name].mean(dim=['x', 'y'], skipna=True).compute()
        
        # Subplot 1: Monthly Climatology
        ax_clim = fig_depth.add_subplot(1, 2, 1)
        if len(da_out_spatial.time) > 151:
            da_clim = da_out_spatial.groupby('time.month').mean(dim='time')
            im = ax_clim.pcolormesh(da_clim.month, da_clim.layer, da_clim.T, shading='auto', cmap='viridis')
            plt.colorbar(im, ax=ax_clim, label=wiemip_units)
            ax_clim.set_xlabel('Month')
            ax_clim.set_ylabel('Depth [Layer Index]')
            ax_clim.set_title('Monthly Climatology Profile')
            ax_clim.invert_yaxis()
        else:
            da_clim = da_out_spatial.mean(dim='time')
            ax_clim.plot(da_clim, da_clim.layer, marker='o')
            ax_clim.set_xlabel(f'{trendy_name} ({wiemip_units})')
            ax_clim.set_ylabel('Depth [Layer Index]')
            ax_clim.set_title('Annual Mean Profile')
            ax_clim.invert_yaxis()
            
        # Subplot 2: Overall Depth Stats
        ax_stats = fig_depth.add_subplot(1, 2, 2)
        da_mean = da_out_spatial.mean(dim='time')
        da_min = da_out_spatial.min(dim='time')
        da_max = da_out_spatial.max(dim='time')
        
        ax_stats.plot(da_mean, da_mean.layer, label='Mean', color='black', linewidth=2)
        ax_stats.plot(da_min, da_min.layer, label='Min', linestyle='--', color='blue')
        ax_stats.plot(da_max, da_max.layer, label='Max', linestyle='--', color='red')
        
        ax_stats.set_xlabel(f'{trendy_name} ({wiemip_units})')
        ax_stats.set_ylabel('Depth [Layer Index]')
        ax_stats.set_title('Overall Time Min/Mean/Max')
        ax_stats.legend()
        ax_stats.invert_yaxis()
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig_depth_file = os.path.join(FIGURES_DIR, f"{var}_depth_climatology.png")
        plt.savefig(fig_depth_file, dpi=150, bbox_inches='tight')
        plt.close(fig_depth)
        print(f"  Saved depth figure to {fig_depth_file}")

print("Done.")
