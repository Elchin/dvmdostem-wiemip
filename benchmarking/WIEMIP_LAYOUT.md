# WIEMIP canonical paths: TEM-GT-benchmarking

Ground-temperature benchmarking uses **two coordinated locations**: the wiemip-postproc VM disk (execution and large data) and the Cursor Project Library (planning, preferences, and status).

## wiemip-postproc (primary execution root)

**Root**: `/mnt/disks/wiemip-data/TEM-GT-benchmarking/`

```
/mnt/disks/wiemip-data/TEM-GT-benchmarking/
├── benchmarking/          # Workflow tree (symlink → repo/benchmarking after setup)
│   ├── data/
│   │   ├── observations/  # PF-AK, station CSVs
│   │   └── climate/
│   │       ├── CRU/       # CRU-TS *.nc (link from wiemip-data/tmp when present)
│   │       └── ERA5/
│   ├── model/
│   │   ├── dvm-dos-tem/   # Cloned/built by 01_setup_model.sh
│   │   ├── inputs/
│   │   ├── outputs/
│   │   └── point_extracts/
│   ├── results/
│   ├── figures/
│   ├── metadata/
│   ├── scripts/
│   ├── PHASE1_WORKFLOW.md
│   └── WIEMIP_LAYOUT.md   # This file
├── repo/                  # git clone: github.com/Elchin/dvmdostem-wiemip
└── store-notes/           # VM ↔ Cursor Context notes (not auto-synced)
```

**CRU staging**: Full-resolution CRU-TS files often land in `/mnt/disks/wiemip-data/tmp/`. The setup script symlinks (or copies) `*.nc` into `benchmarking/data/climate/CRU/` so download and forcing scripts have a stable path.

**Bootstrap script** (idempotent, run on wiemip-postproc):

`benchmarking/scripts/setup_wiemip_tem_gt_benchmarking.sh`

Environment overrides:

| Variable | Default |
|----------|---------|
| `WIEMIP_ROOT` | `/mnt/disks/wiemip-data/TEM-GT-benchmarking` |
| `CRU_TMP_DIR` | `/mnt/disks/wiemip-data/tmp` |
| `WIEMIP_GIT_BRANCH` | `cursor/phase1-benchmarking-setup-ba10` |
| `WIEMIP_REPO_URL` | `https://github.com/Elchin/dvmdostem-wiemip.git` |

## Cursor Project Library (Context)

Use Context for material that should follow the researcher across machines, not multi-GB NetCDF.

| Content | Typical location in Context |
|---------|------------------------------|
| Benchmarking strategy & phases | `docs/ground-temperature-benchmarking-plan.md` |
| Execution preferences (branch, VM root) | `preferences.md` |
| Phase status, inventories, agent notes | `internal/*.md` |
| Tasks and coordination | Project task list |

**Not in Context by default**: CRU grids, PF-AK bulk files, model binaries, run output — keep those under `WIEMIP_ROOT` on wiemip-postproc and track provenance in git (`metadata/data_sources.md`) and commit messages.

## Git vs disk

| Artifact | Where it lives |
|----------|----------------|
| Scripts, small CSVs, docs | `dvmdostem-wiemip` branch `cursor/phase1-benchmarking-setup-ba10` |
| CRU NetCDF, ERA5 extracts, run output | VM disk under `WIEMIP_ROOT` |
| DVM-DOS-TEM source | `benchmarking/model/dvm-dos-tem/` (clone of `Elchin/dvm-dos-tem`, branch `wetland/reburn-switch`) |

## Related WIEMIP paths (other work)

WIEMIP overshoot / 1pctCO2 post-processing in this repository uses GCS-oriented paths in `post-processing/` and is separate from the TEM-GT-benchmarking tree above.

## Quick command cheat sheet

From `WIEMIP_ROOT`:

```bash
# One-time (or repeat) layout
bash repo/benchmarking/scripts/setup_wiemip_tem_gt_benchmarking.sh

cd benchmarking/scripts/download_data
python3 download_cru.py --cru-dir ../../data/climate/CRU

cd ../..
./01_setup_model.sh
```

See `PHASE1_WORKFLOW.md` for the full Phase 1 sequence.