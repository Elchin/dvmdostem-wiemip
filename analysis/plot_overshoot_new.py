import argparse
import os
import glob
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Plot overshoot timeseries data.")
    parser.add_argument("--var", required=True, help="Variable to plot (e.g., alt, gpp)")
    parser.add_argument("--agg", default="mean", choices=["mean", "sum"], help="Spatial aggregation method")
    parser.add_argument("--freq", required=True, choices=["yr", "mon"], help="Frequency of the source data (yr or mon)")
    parser.add_argument("--layer", type=int, default=None, help="Optional index to slice 4D data (e.g., --layer 0)")
    parser.add_argument("--outdir", required=True, help="Output directory for figures")
    parser.add_argument(
        "--data-root",
        default="/mnt/disks/wiemip-data/newly_processed",
        help="Parent directory containing DVM-DOS-TEM_<scenario>/<input-subdir>",
    )
    parser.add_argument(
        "--input-subdir",
        default="filtered",
        help=(
            "Subfolder under each DVM-DOS-TEM_<scenario> case (default: filtered). "
            "Falls back to filtered_wiemip_output if missing."
        ),
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=None,
        help=(
            "Scenarios to plot (e.g. ctrl historic l). Default: all overshoot cases "
            "that exist under --data-root."
        ),
    )
    return parser.parse_args()

def _case_input_dirs(data_root, scenario, input_subdir):
    case = os.path.join(data_root, f"DVM-DOS-TEM_{scenario}")
    candidates = [input_subdir]
    if input_subdir != "filtered_wiemip_output":
        candidates.append("filtered_wiemip_output")
    if input_subdir != "filtered":
        candidates.append("filtered")
    seen = set()
    dirs = []
    for name in candidates:
        if name in seen:
            continue
        seen.add(name)
        path = os.path.join(case, name)
        if os.path.isdir(path):
            dirs.append(path)
    return dirs


def get_file_path(data_root, scenario, var, freq, input_subdir):
    filename = f"DVM-DOS-TEM_{scenario}_{var}_{freq}_05.nc"
    for base_dir in _case_input_dirs(data_root, scenario, input_subdir):
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            return path
        search_pattern = os.path.join(base_dir, f"*_{var}_{freq}_*.nc")
        matches = glob.glob(search_pattern)
        if matches:
            return matches[0]
    return None

def process_scenario(data_root, scenario, var, freq, agg_method, layer, start_year, input_subdir):
    path = get_file_path(data_root, scenario, var, freq, input_subdir)
    if not path:
        print(f"Warning: Data not found for scenario {scenario}")
        return None
    
    print(f"Processing {scenario} from {path}...")
    ds = xr.open_dataset(path, decode_times=False)
    
    if var not in ds.data_vars:
        print(f"Error: Variable {var} not found in {path}")
        return None
    
    da = ds[var]
    
    # Handle layer slicing for 4D data
    dims = da.dims
    spatial_dims = ['y', 'x']
    other_dims = [d for d in dims if d not in spatial_dims and d != 'time']
    
    if len(other_dims) > 0:
        if layer is not None:
            dim_to_slice = other_dims[0]
            da = da.isel({dim_to_slice: layer})
        else:
            print(f"Warning: {var} has extra dimensions {other_dims}. Please specify --layer to slice. Slicing index 0 by default.")
            dim_to_slice = other_dims[0]
            da = da.isel({dim_to_slice: 0})
            
    # Extract units
    try:
        units = da.attrs.get('units', '')
    except:
        units = ''
            
    # Spatial aggregation
    if agg_method == "mean":
        da_agg = da.mean(dim=spatial_dims, skipna=True)
    elif agg_method == "sum":
        da_agg = da.sum(dim=spatial_dims, skipna=True)
    
    # Reconstruct time axis
    time_len = len(da_agg['time'])
    
    if freq == 'yr':
        years = np.arange(start_year, start_year + time_len)
        da_agg['time'] = years
        df = da_agg.to_dataframe(name=var).reset_index()
        return df, None, units
    elif freq == 'mon':
        years = start_year + np.arange(time_len) // 12
        months = (np.arange(time_len) % 12) + 1
        
        # Create a pandas dataframe
        df = da_agg.to_dataframe(name=var).reset_index()
        df['year'] = years
        df['month'] = months
        
        # Yearly average
        df_yearly = df.groupby('year')[var].mean().reset_index()
        
        # Monthly climatology
        df_seasonal = df.groupby('month')[var].mean().reset_index()
        
        return df_yearly, df_seasonal, units

def default_scenarios(data_root, input_subdir):
    historic = ['ctrl', 'historic']
    future = ['l', 'hl', 'hl_cf', 'm']
    present = []
    for s in historic + future:
        if _case_input_dirs(data_root, s, input_subdir):
            present.append(s)
    return present


def start_year_for_scenario(scenario):
    if scenario in ('ctrl', 'historic'):
        return 1850
    return 2024


def main():
    args = parse_args()
    data_root = os.path.abspath(args.data_root)
    input_subdir = args.input_subdir
    scenarios = args.scenarios if args.scenarios else default_scenarios(data_root, input_subdir)

    results = {}
    plot_units = ""

    for scenario in scenarios:
        start_year = start_year_for_scenario(scenario)
        res = process_scenario(
            data_root,
            scenario,
            args.var,
            args.freq,
            args.agg,
            args.layer,
            start_year,
            input_subdir,
        )
        if res:
            results[scenario] = res[:2]
            if not plot_units and res[2]:
                plot_units = res[2]
            
    if not results:
        print("No data processed. Exiting.")
        return
        
    y_label = f'{args.var} ({args.agg})'
    if plot_units:
        y_label += f' [{plot_units}]'
        
    os.makedirs(args.outdir, exist_ok=True)
        
    # Plotting
    if args.freq == 'yr':
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for scenario, (df, _) in results.items():
            ax.plot(df['time'], df[args.var], label=scenario)
            
        ax.set_xlabel('Year')
        ax.set_ylabel(y_label)
        ax.set_title(f'Overshoot Timeseries: {args.var}')
        ax.legend()
        ax.grid(True)
        
        layer_suffix = f"_layer{args.layer}" if args.layer is not None else ""
        out_path = os.path.join(args.outdir, f"overshoot_{args.var}_yr_{args.agg}{layer_suffix}.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        print(f"Saved plot to {out_path}")
        
    elif args.freq == 'mon':
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'width_ratios': [2, 1]})
        
        # Timeseries
        for scenario, (df_yearly, _) in results.items():
            ax1.plot(df_yearly['year'], df_yearly[args.var], label=scenario)
            
        ax1.set_xlabel('Year')
        ax1.set_ylabel(y_label)
        ax1.set_title(f'Yearly Average Timeseries: {args.var}')
        ax1.legend()
        ax1.grid(True)
        
        # Seasonality
        for scenario, (_, df_seasonal) in results.items():
            ax2.plot(df_seasonal['month'], df_seasonal[args.var], label=scenario, marker='o')
            
        ax2.set_xlabel('Month')
        ax2.set_ylabel(y_label)
        ax2.set_title('Monthly Climatology')
        ax2.set_xticks(range(1, 13))
        ax2.set_xticklabels(['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'])
        ax2.grid(True)
        ax2.legend()
        
        layer_suffix = f"_layer{args.layer}" if args.layer is not None else ""
        out_path = os.path.join(args.outdir, f"overshoot_{args.var}_mon_{args.agg}{layer_suffix}.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        print(f"Saved plot to {out_path}")

if __name__ == "__main__":
    main()
