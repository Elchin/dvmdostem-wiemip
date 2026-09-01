import os
import glob
import csv
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import netCDF4 as nc
import gc
import psutil

# Force xarray to keep data on disk when doing large reductions
xr.set_options(keep_attrs=True)

# Configuration
CONFIG_SH_PATH = os.path.expanduser('~/dvmdostem-wiemip/post-processing/config.sh')
CSV_PATH = os.path.expanduser('~/dvmdostem-wiemip/post-processing/output_conversion_table.csv')
VEG_PATH = os.path.expanduser('~/dvmdostem-wiemip/post-processing/wetland.nc')

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
process_type = "noProcess"
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
        elif line.startswith('export PROCESS='):
            process_type = line.split('=')[1].strip('\'"')

# Parse CSV
var_config = {}
math_vars = []
all_rows = []

with open(CSV_PATH, 'r') as f:
    reader = csv.reader(f)
    header = next(reader) # header 1
    
    for row in reader:
        if len(row) > 17:
            var_class = row[5].strip()
            if var_class == '5_Ignore_for_now':
                continue
            all_rows.append(row)

# First pass: add variables directly matching VAR_NAMES
included_wiemip_names = set()
for row in all_rows:
    wiemip_name = row[1].strip()
    variable1 = row[6].strip()
    if variable1 in var_names or wiemip_name in var_names:
        included_wiemip_names.add(wiemip_name)
        # Also add variable1 to included set in case a math var depends on the TEM name directly
        included_wiemip_names.add(variable1)

# Second pass: add 4_Math variables if their dependencies are met
for row in all_rows:
    var_class = row[5].strip()
    wiemip_name = row[1].strip()
    variable1 = row[6].strip()
    variable2 = row[7].strip()
    
    if var_class == '4_Math':
        if variable1 in included_wiemip_names and variable2 in included_wiemip_names:
            included_wiemip_names.add(wiemip_name)

# Now build the config
for row in all_rows:
    wiemip_name = row[1].strip()
    if wiemip_name in included_wiemip_names:
        var_class = row[5].strip()
        conf = {
            'description': row[0].strip(),
            'wiemip_name': wiemip_name,
            'wiemip_units': row[2].strip(),
            'tem_units': row[3].strip(),
            'frequency': row[4].strip(),
            'var_class': var_class,
            'variable1': row[6].strip(),
            'variable2': row[7].strip(),
            'operation': row[8].strip(),
            'g_to_kg': row[11].strip().upper() == 'TRUE',
            'per_mo_to_s': row[12].strip().upper() == 'TRUE',
            'per_day_to_s': row[13].strip().upper() == 'TRUE',
            'c_to_k': row[14].strip().upper() == 'TRUE',
            'mm_to_kg': row[15].strip().upper() == 'TRUE',
            'vwc_to_kg': row[16].strip().upper() == 'TRUE',
            'merge': row[17].strip() == '1'
        }
        var_config[wiemip_name] = conf
        if var_class == '4_Math':
            math_vars.append(wiemip_name)

# Sort the configuration so that 4_Math variables are processed last
processing_order = [v for v in var_config.keys() if v not in math_vars] + math_vars

# Load vegetation data
ds_veg = xr.open_dataset(VEG_PATH).rename({'X': 'x', 'Y': 'y'})
veg_cov = ds_veg['veg_pct_cov'].drop_vars(['x', 'y'], errors='ignore')
veg_fraction_np = (veg_cov.values * 0.01).astype(np.float32)

def apply_unit_conversions(out_t, conf, days_in_month=None, layerdz=None):
    if conf['g_to_kg']:
        out_t *= 0.001
    if conf['mm_to_kg']:
        # 1 mm = 1 kg/m2
        pass # No numerical change, just unit change
    if conf['per_mo_to_s']:
        if days_in_month is not None:
            # Reshape days_in_month to broadcast over out_t
            # out_t shape is usually (time, y, x) or (time, pft, y, x)
            # days_in_month shape is (time,)
            dim_expand = [slice(None)] + [np.newaxis] * (out_t.ndim - 1)
            out_t /= (days_in_month[tuple(dim_expand)] * 86400.0)
        else:
            out_t /= (30.4 * 86400.0)
    if conf['per_day_to_s']:
        out_t /= 86400.0
    if conf['c_to_k']:
        out_t += 273.15
    if conf['vwc_to_kg'] and layerdz is not None:
        # VWC is m3/m3. Multiply by layer thickness (m) and density of water (1000 kg/m3)
        # layerdz shape is (time, layer, y, x)
        out_t *= (layerdz * 1000.0)
    return out_t

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

# Helper to find the WIEMIP name for a given variable (which might be a TEM name or WIEMIP name)
def get_wiemip_name(var_name):
    if var_name in var_config:
        return var_name
    for w_name, conf in var_config.items():
        if conf['variable1'] == var_name:
            return w_name
    return var_name

for wiemip_name in processing_order:
    conf = var_config[wiemip_name]
    var_class = conf['var_class']
    variable1 = conf['variable1']
    variable2 = conf['variable2']
    merge = conf['merge']
    
    print(f"Processing {wiemip_name} (Class: {var_class})...")
    
    if var_class in ['1_Units_only', '2_Sum_by_PFT', '3_Sum_by_layer']:
        # Find files
        base_files = glob.glob(os.path.join(LOCAL_BASE_RUN, f"{variable1}_*tr*.nc"))
        wet_files = glob.glob(os.path.join(LOCAL_WET_RUN, f"{variable1}_*tr*.nc"))
        
        if not base_files:
            print(f"No base file found for {variable1}")
            continue
            
        with xr.open_dataset(base_files[0]) as ds_base:
            dims = list(ds_base[variable1].dims)
            num_times = len(ds_base.time) if 'time' in dims else 1
            if 'time' in dims:
                days_in_month = ds_base.time.dt.days_in_month.values
            else:
                days_in_month = None
        
        base_basename = os.path.basename(base_files[0])
        parts = base_basename.split('_')
        frequency = parts[1] if len(parts) > 1 else 'unknown'
        
        nc_filename = f"DVMDOSTEM_{gcm_pattern}_{experiment}_{wiemip_name}_{frequency}_{process_type}_0.5deg.nc"
        out_file = os.path.join(LOCAL_WIEMIP_OUTPUT, nc_filename)
        
        if os.path.exists(out_file):
            os.remove(out_file)
            
        print(f"  Streaming to {out_file}...")
        
        do_merge = merge and bool(wet_files)
        
        if 'time' in dims:
            with nc.Dataset(out_file, 'w', format='NETCDF4') as nc_out:
                with nc.Dataset(base_files[0], 'r') as nc_base:
                    # Create dimensions
                    for dim_name, dim in nc_base.dimensions.items():
                        if var_class == '2_Sum_by_PFT' and dim_name == 'pft':
                            continue
                        if var_class == '3_Sum_by_layer' and dim_name == 'layer':
                            continue
                        nc_out.createDimension(dim_name, len(dim) if not dim.isunlimited() else None)
                        
                    # Copy variables except the main one
                    for v_name, v_in in nc_base.variables.items():
                        if v_name != variable1:
                            if var_class == '2_Sum_by_PFT' and 'pft' in v_in.dimensions:
                                continue
                            if var_class == '3_Sum_by_layer' and 'layer' in v_in.dimensions:
                                continue
                            v_out = nc_out.createVariable(v_name, v_in.datatype, v_in.dimensions, zlib=True)
                            v_out.setncatts({k: v_in.getncattr(k) for k in v_in.ncattrs()})
                            v_out[:] = v_in[:]
                            
                    v_base = nc_base.variables[variable1]
                    
                    fill_val = None
                    if hasattr(v_base, '_FillValue'):
                        fill_val = np.float32(v_base._FillValue)
                        
                    out_dims = tuple(d for d in v_base.dimensions if not (var_class == '2_Sum_by_PFT' and d == 'pft') and not (var_class == '3_Sum_by_layer' and d == 'layer'))
                    
                    # Determine chunking
                    chunking = v_base.chunking()
                    if chunking == 'contiguous':
                        chunking = None
                    elif isinstance(chunking, list) or isinstance(chunking, tuple):
                        out_chunking = []
                        for i, d in enumerate(v_base.dimensions):
                            if d in out_dims:
                                out_chunking.append(chunking[i])
                        chunking = tuple(out_chunking)
                        
                    v_out = nc_out.createVariable(wiemip_name, np.float32, out_dims, zlib=True, chunksizes=chunking, fill_value=fill_val)
                    
                    atts = {}
                    for k in v_base.ncattrs():
                        if k != '_FillValue':
                            val = v_base.getncattr(k)
                            if isinstance(val, (float, np.floating)):
                                val = np.float32(val)
                            atts[k] = val
                    v_out.setncatts(atts)
                    v_out.units = conf['wiemip_units']
                    
                    nc_wet = nc.Dataset(wet_files[0], 'r') if do_merge else None
                    v_wet = nc_wet.variables[variable1] if nc_wet else None
                    
                    # Load LAYERDZ if needed
                    nc_layerdz = None
                    v_layerdz = None
                    if conf['vwc_to_kg']:
                        layerdz_files = glob.glob(os.path.join(LOCAL_BASE_RUN, "LAYERDZ_*tr*.nc"))
                        if layerdz_files:
                            nc_layerdz = nc.Dataset(layerdz_files[0], 'r')
                            v_layerdz = nc_layerdz.variables['LAYERDZ']
                    
                    time_chunk = 12
                    if isinstance(v_base.chunking(), list) or isinstance(v_base.chunking(), tuple):
                        time_chunk = v_base.chunking()[0]
                        
                    slice_bytes = np.prod(v_base.shape[1:]) * 4
                    while time_chunk * slice_bytes > 4 * 1024**3 and time_chunk > 1:
                        time_chunk //= 2
                        
                    for t_start in range(0, num_times, time_chunk):
                        t_end = min(t_start + time_chunk, num_times)
                        
                        process = psutil.Process(os.getpid())
                        print(f"      Processing steps {t_start} to {t_end}... Mem: {process.memory_info().rss / 1024**3:.2f} GB")
                        
                        base_t = np.array(v_base[t_start:t_end, ...], dtype=np.float32)
                        
                        is_missing = None
                        if fill_val is not None:
                            is_missing = (base_t == fill_val)
                            
                        out_t = base_t.copy()
                        
                        if do_merge:
                            wet_t = np.array(v_wet[t_start:t_end, ...], dtype=np.float32)
                            valid_t_len = wet_t.shape[0]
                            
                            if fill_val is not None:
                                wet_valid = (wet_t != fill_val) & ~np.isnan(wet_t)
                            else:
                                wet_valid = ~np.isnan(wet_t)
                            
                            base_t_slice = base_t[:valid_t_len, ...]
                            out_t_slice = out_t[:valid_t_len, ...]
                            
                            merged_t = (base_t_slice * veg_fraction_np) + (wet_t * (1.0 - veg_fraction_np))
                            out_t_slice[wet_valid] = merged_t[wet_valid]
                            
                            del wet_t, wet_valid, merged_t, base_t_slice, out_t_slice
                            
                        # Apply unit conversions
                        layerdz_t = None
                        if v_layerdz is not None:
                            layerdz_t = np.array(v_layerdz[t_start:t_end, ...], dtype=np.float32)
                            
                        out_t = apply_unit_conversions(out_t, conf, days_in_month[t_start:t_end], layerdz_t)
                        
                        # Apply aggregations
                        if var_class == '2_Sum_by_PFT':
                            pft_axis = v_base.dimensions.index('pft')
                            # Sum, but we need to handle missing values
                            if is_missing is not None:
                                out_t[is_missing] = np.nan
                            out_t = np.nansum(out_t, axis=pft_axis)
                            if is_missing is not None:
                                is_missing_agg = np.all(is_missing, axis=pft_axis)
                                out_t[is_missing_agg] = fill_val
                        elif var_class == '3_Sum_by_layer':
                            layer_axis = v_base.dimensions.index('layer')
                            if is_missing is not None:
                                out_t[is_missing] = np.nan
                            out_t = np.nansum(out_t, axis=layer_axis)
                            if is_missing is not None:
                                is_missing_agg = np.all(is_missing, axis=layer_axis)
                                out_t[is_missing_agg] = fill_val
                        else:
                            if is_missing is not None:
                                out_t[is_missing] = fill_val
                                
                        v_out[t_start:t_end, ...] = out_t
                        del base_t, out_t, is_missing, layerdz_t
                        
                        nc_out.sync()
                        gc.collect()
                            
                    if nc_wet:
                        nc_wet.close()
                    if nc_layerdz:
                        nc_layerdz.close()
        else:
            # No time dimension
            ds_base = xr.open_dataset(base_files[0])
            base_slice = ds_base[variable1].compute()
            base_vals = base_slice.values.astype(np.float32)
            
            if do_merge:
                ds_wet = xr.open_dataset(wet_files[0])
                wet_slice = ds_wet[variable1].compute()
                wet_vals = wet_slice.values.astype(np.float32)
                has_wet = ~np.isnan(wet_vals)
                merged_vals = (base_vals * veg_fraction_np + wet_vals * (1.0 - veg_fraction_np)).astype(np.float32)
                out_vals = np.where(has_wet, merged_vals, base_vals).astype(np.float32)
                ds_wet.close()
            else:
                out_vals = base_vals
                
            layerdz_vals = None
            if conf['vwc_to_kg']:
                layerdz_files = glob.glob(os.path.join(LOCAL_BASE_RUN, "LAYERDZ_*tr*.nc"))
                if layerdz_files:
                    ds_layerdz = xr.open_dataset(layerdz_files[0])
                    layerdz_vals = ds_layerdz['LAYERDZ'].compute().values.astype(np.float32)
                    ds_layerdz.close()
                    
            out_vals = apply_unit_conversions(out_vals, conf, None, layerdz_vals)
            
            da_out = base_slice.copy(data=out_vals)
            
            if var_class == '2_Sum_by_PFT':
                da_out = da_out.sum(dim='pft', skipna=True, min_count=1)
            elif var_class == '3_Sum_by_layer':
                da_out = da_out.sum(dim='layer', skipna=True, min_count=1)
                
            da_out.values = da_out.values.astype(np.float32)
            da_out.attrs['units'] = conf['wiemip_units']
            da_out.name = wiemip_name
            
            ds_out = xr.Dataset({wiemip_name: da_out})
            # Copy relevant coords
            for coord in da_out.coords:
                ds_out = ds_out.assign_coords({coord: da_out.coords[coord]})
                
            ds_out.to_netcdf(out_file, engine='netcdf4')
            ds_base.close()
            ds_out.close()
            
        import gc
        gc.collect()
        
        # Plotting
        print("  Generating figure...")
        fig = plt.figure(figsize=(18, 15))
        
        ds_base_plot = xr.open_dataset(base_files[0])
        overall_shape = ds_base_plot[variable1].shape
        
        agg = time_aggregation.get(wiemip_name, time_aggregation.get(variable1, 'mean'))
        
        fig.suptitle(f'Variable: {variable1} -> {wiemip_name} (Merge: {merge}) | Shape: {overall_shape}', fontsize=16)
        
        plot_row(fig, 0, variable1, ds_base_plot, f'Base Run ({variable1})', agg, ds_base_plot[variable1].attrs.get('units', ''))
        
        if wet_files:
            ds_wet_plot = xr.open_dataset(wet_files[0])
            plot_row(fig, 1, variable1, ds_wet_plot, f'Wet Run ({variable1})', agg, ds_wet_plot[variable1].attrs.get('units', ''))
            ds_wet_plot.close()
        else:
            plot_row(fig, 1, variable1, None, f'Wet Run ({variable1})', agg, '')
            
        ds_out_saved = xr.open_dataset(out_file)
        plot_row(fig, 2, wiemip_name, ds_out_saved, f'WIEMIP Output ({wiemip_name})', agg, conf['wiemip_units'])
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        fig_file = os.path.join(FIGURES_DIR, f"{wiemip_name}_summary.png")
        plt.savefig(fig_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved figure to {fig_file}")
        
        ds_base_plot.close()
        
        if 'layer' in ds_out_saved[wiemip_name].dims:
            print(f"  Generating depth climatology figure for {wiemip_name}...")
            fig_depth = plt.figure(figsize=(15, 6))
            fig_depth.suptitle(f'{wiemip_name} - Depth Profile Climatology & Stats', fontsize=16)
            
            print(f"    Computing spatial mean for depth profiles (this may take a moment)...")
            da_out_spatial = ds_out_saved[wiemip_name].mean(dim=['x', 'y'], skipna=True).compute()
            
            ax_clim = fig_depth.add_subplot(1, 2, 1)
            if len(da_out_spatial.time) > 151:
                da_clim = da_out_spatial.groupby('time.month').mean(dim='time')
                im = ax_clim.pcolormesh(da_clim.month, da_clim.layer, da_clim.T, shading='auto', cmap='viridis')
                plt.colorbar(im, ax=ax_clim, label=conf['wiemip_units'])
                ax_clim.set_xlabel('Month')
                ax_clim.set_ylabel('Depth [Layer Index]')
                ax_clim.set_title('Monthly Climatology Profile')
                ax_clim.invert_yaxis()
            else:
                da_clim = da_out_spatial.mean(dim='time')
                ax_clim.plot(da_clim, da_clim.layer, marker='o')
                ax_clim.set_xlabel(f"{wiemip_name} ({conf['wiemip_units']})")
                ax_clim.set_ylabel('Depth [Layer Index]')
                ax_clim.set_title('Annual Mean Profile')
                ax_clim.invert_yaxis()
                
            ax_stats = fig_depth.add_subplot(1, 2, 2)
            da_mean = da_out_spatial.mean(dim='time')
            da_min = da_out_spatial.min(dim='time')
            da_max = da_out_spatial.max(dim='time')
            
            ax_stats.plot(da_mean, da_mean.layer, label='Mean', color='black', linewidth=2)
            ax_stats.plot(da_min, da_min.layer, label='Min', linestyle='--', color='blue')
            ax_stats.plot(da_max, da_max.layer, label='Max', linestyle='--', color='red')
            
            ax_stats.set_xlabel(f"{wiemip_name} ({conf['wiemip_units']})")
            ax_stats.set_ylabel('Depth [Layer Index]')
            ax_stats.set_title('Overall Time Min/Mean/Max')
            ax_stats.legend()
            ax_stats.invert_yaxis()
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            fig_depth_file = os.path.join(FIGURES_DIR, f"{wiemip_name}_depth_climatology.png")
            plt.savefig(fig_depth_file, dpi=150, bbox_inches='tight')
            plt.close(fig_depth)
            print(f"  Saved depth figure to {fig_depth_file}")

        ds_out_saved.close()
    elif var_class == '4_Math':
        print(f"  Math operation: {wiemip_name} = {variable1} {conf['operation']} {variable2}")
        
        w_var1 = get_wiemip_name(variable1)
        w_var2 = get_wiemip_name(variable2)
        
        file1 = glob.glob(os.path.join(LOCAL_WIEMIP_OUTPUT, f"*_{w_var1}_*.nc"))
        file2 = glob.glob(os.path.join(LOCAL_WIEMIP_OUTPUT, f"*_{w_var2}_*.nc"))
        
        if not file1 or not file2:
            print(f"  Missing processed files for {w_var1} or {w_var2}. Skipping.")
            continue
            
        ds1 = xr.open_dataset(file1[0])
        ds2 = xr.open_dataset(file2[0])
        
        da1 = ds1[w_var1]
        da2 = ds2[w_var2]
        
        # Ensure they have the same coords before math
        da2 = da2.interp_like(da1) if not da1.coords.equals(da2.coords) else da2
        
        op = conf['operation'].lower()
        if op == 'add':
            da_out = da1 + da2
        elif op == 'subtract':
            da_out = da1 - da2
        elif op == 'multiply':
            da_out = da1 * da2
        elif op == 'divide':
            da_out = da1 / da2
        else:
            print(f"  Unknown operation {op}. Skipping.")
            continue
            
        da_out.name = wiemip_name
        da_out.attrs['units'] = conf['wiemip_units']
        
        # Generate standard output filename
        frequency = conf['frequency']
        nc_filename = f"DVMDOSTEM_{gcm_pattern}_{experiment}_{wiemip_name}_{frequency}_{process_type}_0.5deg.nc"
        out_file = os.path.join(LOCAL_WIEMIP_OUTPUT, nc_filename)
        
        ds_out = xr.Dataset({wiemip_name: da_out})
        for coord in da_out.coords:
            ds_out = ds_out.assign_coords({coord: da_out.coords[coord]})
            
        ds_out.to_netcdf(out_file, engine='netcdf4')
        
        # Plotting for 4_Math
        print("  Generating figure...")
        fig = plt.figure(figsize=(18, 15))
        
        overall_shape = ds1[w_var1].shape
        agg = time_aggregation.get(wiemip_name, 'mean')
        
        fig.suptitle(f'Math Operation: {wiemip_name} = {w_var1} {conf["operation"]} {w_var2} | Shape: {overall_shape}', fontsize=16)
        
        plot_row(fig, 0, w_var1, ds1, f'Input 1 ({w_var1})', agg, ds1[w_var1].attrs.get('units', ''))
        plot_row(fig, 1, w_var2, ds2, f'Input 2 ({w_var2})', agg, ds2[w_var2].attrs.get('units', ''))
        plot_row(fig, 2, wiemip_name, ds_out, f'Math Result ({wiemip_name})', agg, conf['wiemip_units'])
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        fig_file = os.path.join(FIGURES_DIR, f"{wiemip_name}_summary.png")
        plt.savefig(fig_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved figure to {fig_file}")
        
        ds1.close()
        ds2.close()
        ds_out.close()
        
        import gc
        gc.collect()

print("Done.")
