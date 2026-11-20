# TEM-GT-benchmarking on wiemip-postproc

**Canonical root**: `/mnt/disks/wiemip-data/TEM-GT-benchmarking/`

This tree is the single workspace for Phase 1 ground-temperature benchmarking: git checkout, observation and climate data, model build, runs, metrics, and figures.

## Directory map (under `benchmarking/`)

| Path | Purpose |
|------|---------|
| `data/observations/` | PF-AK and station extracts for validation |
| `data/climate/CRU/` | CRU-TS global grids (often symlinked from `/mnt/disks/wiemip-data/tmp/`) |
| `data/climate/ERA5/` | Station-scale ERA5 downloads |
| `model/inputs/` | DVM-DOS-TEM single-pixel (or gridded) input NetCDF |
| `model/outputs/` | Spin-up and transient run output |
| `model/point_extracts/` | Model series at observation depths |
| `results/` | Tables, metrics, intermediate analysis products |
| `figures/` | Validation plots and maps |
| `metadata/` | Station inventory, data source notes |
| `scripts/` | Download, setup, and (future) prepare/run/metrics scripts |

Sibling at canonical root:

| Path | Purpose |
|------|---------|
| `repo/` | `dvmdostem-wiemip` git checkout (branch `cursor/phase1-benchmarking-setup-ba10`) |
| `store-notes/` | How this VM layout maps to Cursor Project Library |

## Bootstrap

On **wiemip-postproc**:

```bash
bash /mnt/disks/wiemip-data/TEM-GT-benchmarking/repo/benchmarking/scripts/setup_wiemip_tem_gt_benchmarking.sh
```

Or from a fresh machine after cloning only the script:

```bash
export WIEMIP_ROOT=/mnt/disks/wiemip-data/TEM-GT-benchmarking
bash benchmarking/scripts/setup_wiemip_tem_gt_benchmarking.sh
```

## References

- Layout detail: `WIEMIP_LAYOUT.md` (in this directory)
- Phase 1 steps: `PHASE1_WORKFLOW.md`
- Project plan (Cursor Context): `docs/ground-temperature-benchmarking-plan.md` in the TEM-dev Project Library