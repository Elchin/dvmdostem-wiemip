# WIEMIP workstation bootstrap

Use this guide to work **entirely on wiemip-postproc** for TEM ground-temperature benchmarking (Phase 1), while keeping plans and decisions in the Cursor Project Library on your Mac.

## What runs where

| Activity | wiemip-postproc | Cursor Project Library (Context) |
|----------|-----------------|----------------------------------|
| Git checkout, scripts, small CSVs | `WIEMIP_ROOT/repo/` | Same branch via GitHub / Cloud Agents |
| CRU NetCDF, ERA5, PF-AK bulk, model runs | `WIEMIP_ROOT/benchmarking/` | Not synced (too large) |
| Benchmarking plan, phases, preferences | Copy optional → `store-notes/` | `docs/ground-temperature-benchmarking-plan.md`, `preferences.md` |
| Phase status, agent coordination | Git + `metadata/` | `internal/*.md`, task list |
| Interactive Cursor coding on the VM | SSH / Remote to wiemip-postproc | Link the same **TEM-dev** Project (see below) |

**Canonical execution root**: `/mnt/disks/wiemip-data/TEM-GT-benchmarking/`  
(override with `WIEMIP_ROOT` if needed.)

## One-stop bootstrap on wiemip-postproc

After the repo exists (minimal clone or prior setup), run:

```bash
export WIEMIP_ROOT=/mnt/disks/wiemip-data/TEM-GT-benchmarking

# Optional: path where you scp'd Mac benchmarking data (see next section)
export MAC_TEM_GT="${WIEMIP_ROOT}/from-mac/TEM-GT-benchmarking"

# Optional: folder with copied Context `docs/` and `preferences.md`
export CONTEXT_DOCS="${WIEMIP_ROOT}/from-mac/context-snapshot"

bash "${WIEMIP_ROOT}/repo/benchmarking/scripts/bootstrap_wiemip_workstation.sh"
```

The bootstrap script:

1. Runs `setup_wiemip_tem_gt_benchmarking.sh` (idempotent layout, git pull, CRU from `wiemip-data/tmp`).
2. If `MAC_TEM_GT` exists, merges **observations** and **CRU** into `benchmarking/data/`.
3. If `CONTEXT_DOCS` is set, copies docs into `store-notes/`.
4. Prints the Phase 1 checklist (model build, CRU extract, workflow doc).

### Optional environment variables

| Variable | Purpose |
|----------|---------|
| `MAC_TEM_GT` | Directory on wiemip containing Mac-copied PF-AK, station CSVs, and/or CRU (see layout hints below). |
| `CONTEXT_DOCS` | Snapshot of Cursor Agent Store: `docs/` and `preferences.md`. |
| `WIEMIP_ROOT` | Default `/mnt/disks/wiemip-data/TEM-GT-benchmarking`. |
| `WIEMIP_GIT_BRANCH` | Default `cursor/phase1-benchmarking-setup-ba10`. |

Recognized layouts under `MAC_TEM_GT`:

- `benchmarking/data/observations/` and `benchmarking/data/climate/CRU/`
- `data/observations/` and `data/climate/CRU/`
- Flat `*.nc` at the root of `MAC_TEM_GT` (copied into CRU)

## Copy data from Mac → wiemip-postproc

Run these **on your Mac** (replace `WIEMIP_USER@wiemip-postproc` with your SSH target). Staging under `from-mac/` keeps the canonical tree clean until bootstrap merges content.

### Benchmarking tree (PF-AK, stations, CRU)

If your Mac already has a partial `TEM-GT-benchmarking` tree:

```bash
# Example local Mac path
MAC_ROOT=~/TEM-GT-benchmarking
WIEMIP_USER=your-user
WIEMIP_HOST=wiemip-postproc.example

rsync -avz --progress \
  "${MAC_ROOT}/benchmarking/data/observations/" \
  "${WIEMIP_USER}@${WIEMIP_HOST}:/mnt/disks/wiemip-data/TEM-GT-benchmarking/from-mac/TEM-GT-benchmarking/benchmarking/data/observations/"

rsync -avz --progress \
  "${MAC_ROOT}/benchmarking/data/climate/CRU/" \
  "${WIEMIP_USER}@${WIEMIP_HOST}:/mnt/disks/wiemip-data/TEM-GT-benchmarking/from-mac/TEM-GT-benchmarking/benchmarking/data/climate/CRU/"
```

Or rsync the whole staging folder:

```bash
rsync -avz --progress \
  "${MAC_ROOT}/" \
  "${WIEMIP_USER}@${WIEMIP_HOST}:/mnt/disks/wiemip-data/TEM-GT-benchmarking/from-mac/TEM-GT-benchmarking/"
```

`scp` alternative (single archive-friendly tree):

```bash
scp -r "${MAC_ROOT}/benchmarking/data/observations" \
  "${WIEMIP_USER}@${WIEMIP_HOST}:/mnt/disks/wiemip-data/TEM-GT-benchmarking/from-mac/TEM-GT-benchmarking/benchmarking/data/"
```

### Cursor Context snapshot (docs + preferences)

Export from the **TEM-dev** Project Agent Store on your Mac (Cursor → Project → Context), or copy the store folder you use for `docs/` and `preferences.md`:

```bash
CONTEXT_SRC=~/path/to/agent-store   # contains docs/ and preferences.md

rsync -avz --progress \
  --include='docs/***' \
  --include='preferences.md' \
  --exclude='*' \
  "${CONTEXT_SRC}/" \
  "${WIEMIP_USER}@${WIEMIP_HOST}:/mnt/disks/wiemip-data/TEM-GT-benchmarking/from-mac/context-snapshot/"
```

Then on **wiemip-postproc**:

```bash
export MAC_TEM_GT=/mnt/disks/wiemip-data/TEM-GT-benchmarking/from-mac/TEM-GT-benchmarking
export CONTEXT_DOCS=/mnt/disks/wiemip-data/TEM-GT-benchmarking/from-mac/context-snapshot
bash /mnt/disks/wiemip-data/TEM-GT-benchmarking/repo/benchmarking/scripts/bootstrap_wiemip_workstation.sh
```

## Cursor agent on wiemip-postproc (same Project)

To continue with Cloud Agents or local Cursor against the VM workspace:

1. Open the **TEM-dev** Project in Cursor (same Project Library as on your Mac).
2. Connect your environment to **wiemip-postproc** (SSH remote host or team WIEMIP environment, per your org setup).
3. Set the workspace folder to `WIEMIP_ROOT/repo` or `WIEMIP_ROOT/benchmarking` so agents edit the same git branch and paths as this bootstrap.

Planning text stays in Context; execution and large files stay under `WIEMIP_ROOT`. After bootstrap, offline copies of Context live in `store-notes/` when you set `CONTEXT_DOCS`.

## Final layout on wiemip-postproc

```
/mnt/disks/wiemip-data/TEM-GT-benchmarking/          # WIEMIP_ROOT
├── benchmarking/          # workflow tree (symlink → repo/benchmarking)
│   ├── data/
│   │   ├── observations/  # PF-AK, station CSVs (git + Mac merge)
│   │   └── climate/
│   │       ├── CRU/       # CRU-TS *.nc (tmp/, Mac, or download_cru.py)
│   │       └── ERA5/
│   ├── model/
│   │   ├── dvm-dos-tem/   # 01_setup_model.sh
│   │   ├── inputs/
│   │   ├── outputs/
│   │   └── point_extracts/
│   ├── results/
│   ├── figures/
│   ├── metadata/
│   ├── scripts/
│   ├── PHASE1_WORKFLOW.md
│   ├── WIEMIP_LAYOUT.md
│   └── WIEMIP_BOOTSTRAP.md   # this file
├── repo/                    # dvmdostem-wiemip (feature branch)
├── store-notes/             # Context snapshot + VM ↔ Library notes
│   ├── README.md            # from setup script
│   ├── docs/                # optional, from CONTEXT_DOCS
│   └── preferences.md       # optional, from CONTEXT_DOCS
└── from-mac/                # optional staging (not required after merge)
    ├── TEM-GT-benchmarking/
    └── context-snapshot/
```

CRU files may also be linked from `/mnt/disks/wiemip-data/tmp/*.nc` by the setup script before or after bootstrap.

## Phase 1 checklist (after bootstrap)

1. **Build model**: `cd benchmarking/scripts && ./01_setup_model.sh`
2. **CRU at stations**: `cd benchmarking/scripts/download_data && python3 download_cru.py --cru-dir ../../data/climate/CRU --stations Deadhorse Imnaviat Smith_Lake_1`
3. **Full workflow**: follow `benchmarking/PHASE1_WORKFLOW.md`

## See also

- `WIEMIP_LAYOUT.md` — path conventions and git vs disk
- `WIEMIP_VM_README.md` — short VM readme installed as `benchmarking/README.md`
- Cursor plan: `docs/ground-temperature-benchmarking-plan.md` in the TEM-dev Project Library