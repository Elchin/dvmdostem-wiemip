#!/usr/bin/env bash
# Idempotent layout for TEM-GT-benchmarking on wiemip-postproc.
# Run on wiemip-postproc only (not cloud agent VMs).
#
# Canonical root: /mnt/disks/wiemip-data/TEM-GT-benchmarking/

set -euo pipefail

ROOT="${WIEMIP_ROOT:-/mnt/disks/wiemip-data/TEM-GT-benchmarking}"
CRU_TMP_DIR="${CRU_TMP_DIR:-/mnt/disks/wiemip-data/tmp}"
REPO_DIR="${ROOT}/repo"
BENCHMARKING_DIR="${ROOT}/benchmarking"
STORE_NOTES_DIR="${ROOT}/store-notes"
REPO_URL="${WIEMIP_REPO_URL:-https://github.com/Elchin/dvmdostem-wiemip.git}"
GIT_BRANCH="${WIEMIP_GIT_BRANCH:-cursor/phase1-benchmarking-setup-ba10}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $*"; }
log_info() { echo -e "${BLUE}[i]${NC} $*"; }

echo "=========================================="
echo "TEM-GT-benchmarking WIEMIP layout setup"
echo "=========================================="
log_info "Root: ${ROOT}"
log_info "CRU temp dir: ${CRU_TMP_DIR}"
log_info "Repo branch: ${GIT_BRANCH}"
echo ""

# --- Top-level directories ---
mkdir -p "${ROOT}" "${REPO_DIR}" "${STORE_NOTES_DIR}"

# --- Git clone or pull (Option A) ---
if [[ -d "${REPO_DIR}/.git" ]]; then
  log_warn "Repo already present at ${REPO_DIR}; fetching and checking out ${GIT_BRANCH}"
  git -C "${REPO_DIR}" fetch origin "${GIT_BRANCH}"
  git -C "${REPO_DIR}" checkout "${GIT_BRANCH}"
  git -C "${REPO_DIR}" pull --ff-only origin "${GIT_BRANCH}" 2>/dev/null || \
    log_warn "Pull skipped (local commits or no fast-forward); continue with current HEAD"
  log_ok "Repository updated"
else
  if [[ -n "$(ls -A "${REPO_DIR}" 2>/dev/null)" ]]; then
    echo "ERROR: ${REPO_DIR} exists but is not a git repository. Move or remove it, then re-run." >&2
    exit 1
  fi
  log_info "Cloning ${REPO_URL} (branch ${GIT_BRANCH})"
  git clone --branch "${GIT_BRANCH}" "${REPO_URL}" "${REPO_DIR}"
  log_ok "Repository cloned"
fi

# --- benchmarking/ at canonical root (symlink to repo/benchmarking when possible) ---
REPO_BENCHMARKING="${REPO_DIR}/benchmarking"
if [[ ! -d "${REPO_BENCHMARKING}" ]]; then
  echo "ERROR: Expected ${REPO_BENCHMARKING} after clone." >&2
  exit 1
fi

if [[ -L "${BENCHMARKING_DIR}" ]]; then
  log_ok "benchmarking/ symlink already exists"
elif [[ -d "${BENCHMARKING_DIR}" ]]; then
  if [[ "$(realpath "${BENCHMARKING_DIR}")" == "$(realpath "${REPO_BENCHMARKING}")" ]]; then
    log_ok "benchmarking/ already points at repo benchmarking tree"
  else
    log_warn "benchmarking/ is a separate directory (not symlinked); keeping existing tree"
  fi
else
  ln -s "${REPO_BENCHMARKING}" "${BENCHMARKING_DIR}"
  log_ok "Symlinked benchmarking/ -> repo/benchmarking"
fi

# --- Expected workflow subdirectories (observations, model, results, figures) ---
EXPECTED_DIRS=(
  "data/observations"
  "data/climate/CRU"
  "data/climate/ERA5"
  "model/inputs"
  "model/outputs"
  "model/point_extracts"
  "results/point_scale"
  "figures/point_scale"
  "metadata"
  "scripts/download_data"
)

for rel in "${EXPECTED_DIRS[@]}"; do
  mkdir -p "${BENCHMARKING_DIR}/${rel}"
done
log_ok "Benchmarking subdirectories ensured"

# --- README (layout on VM) ---
VM_README_SRC="${REPO_DIR}/benchmarking/WIEMIP_VM_README.md"
if [[ -f "${VM_README_SRC}" ]]; then
  cp -f "${VM_README_SRC}" "${BENCHMARKING_DIR}/README.md"
  log_ok "Installed benchmarking/README.md from repo"
else
  log_warn "Missing ${VM_README_SRC}; skipping README copy"
fi

# --- CRU NetCDF from tmp/ -> benchmarking/data/climate/CRU/ ---
CRU_DEST="${BENCHMARKING_DIR}/data/climate/CRU"
mkdir -p "${CRU_DEST}"

link_or_copy_cru() {
  local src="$1"
  local base dest
  base="$(basename "${src}")"
  dest="${CRU_DEST}/${base}"

  if [[ -e "${dest}" ]]; then
    if [[ "$(readlink -f "${dest}" 2>/dev/null || echo "${dest}")" == "$(readlink -f "${src}")" ]]; then
      return 0
    fi
    log_warn "Already present (not same file): ${dest}"
    return 0
  fi

  if ln -s "${src}" "${dest}" 2>/dev/null; then
    log_ok "Linked ${base}"
  else
    cp -a "${src}" "${dest}"
    log_ok "Copied ${base}"
  fi
}

cru_count=0
if [[ -d "${CRU_TMP_DIR}" ]]; then
  shopt -s nullglob
  for nc in "${CRU_TMP_DIR}"/*.nc; do
    link_or_copy_cru "${nc}"
    cru_count=$((cru_count + 1))
  done
  shopt -u nullglob
  if [[ "${cru_count}" -eq 0 ]]; then
    log_warn "No *.nc files in ${CRU_TMP_DIR}; add CRU files or run download_cru.py later"
  else
    log_ok "Linked or copied ${cru_count} CRU *.nc file(s) into data/climate/CRU/"
  fi
else
  log_warn "CRU tmp directory not found: ${CRU_TMP_DIR}"
fi

# --- store-notes: how VM layout relates to Cursor Project Library ---
cat > "${STORE_NOTES_DIR}/README.md" <<'STORE_EOF'
# Cursor Project Library (Context) vs wiemip-postproc

This folder is a **local pointer** on wiemip-postproc. It is not synced automatically with Cursor.

| Topic | On wiemip-postproc | In Cursor Project Library |
|-------|--------------------|---------------------------|
| Canonical execution root | `/mnt/disks/wiemip-data/TEM-GT-benchmarking/` | Preference only (see project `preferences.md`) |
| Benchmarking plan & phase notes | `repo/benchmarking/PHASE1_WORKFLOW.md`, `repo/benchmarking/WIEMIP_LAYOUT.md` | `docs/ground-temperature-benchmarking-plan.md` |
| Workflow status / inventories | Git history + repo metadata | `internal/phase1-*.md`, task list |
| Code & scripts | `repo/` git checkout | Same branch via GitHub / Cloud Agents |

Edit code and data on the VM under this root; use the Project Library for planning, decisions, and cross-machine notes.
STORE_EOF
log_ok "Wrote store-notes/README.md"

echo ""
echo "=========================================="
echo "Layout complete"
echo "=========================================="
echo "  ${ROOT}/"
echo "    benchmarking/   -> workflow, data, results (symlink to repo/benchmarking)"
echo "    repo/           -> dvmdostem-wiemip (${GIT_BRANCH})"
echo "    store-notes/    -> Context vs VM notes"
echo ""
echo "Next steps (paths relative to ${ROOT} unless noted):"
echo ""
echo "  1) CRU station extracts / validation:"
echo "     cd benchmarking/scripts/download_data"
echo "     python3 download_cru.py --cru-dir ../data/climate/CRU \\"
echo "       --stations Deadhorse Imnaviat Smith_Lake_1"
echo ""
echo "  2) PF-AK + ERA5 acquisition (Phase 1):"
echo "     cd benchmarking/scripts/download_data"
echo "     ./00_master_download.sh"
echo "     # or CRU-focused: ./01_master_download_cru.sh"
echo ""
echo "  3) Build DVM-DOS-TEM (wetland/reburn-switch):"
echo "     cd benchmarking/scripts"
echo "     ./01_setup_model.sh"
echo ""
echo "  4) Full workflow doc:"
echo "     less repo/benchmarking/PHASE1_WORKFLOW.md"
echo "     less repo/benchmarking/WIEMIP_LAYOUT.md"
echo ""