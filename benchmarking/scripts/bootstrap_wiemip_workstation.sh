#!/usr/bin/env bash
# One-stop bootstrap for TEM-GT-benchmarking on wiemip-postproc.
# Run on wiemip-postproc only (not cloud agent VMs).
#
# Optional environment variables (user-supplied paths after scp/rsync from Mac):
#
#   MAC_TEM_GT    Local directory on wiemip where Mac material was copied
#                 (e.g. ~/from-mac/TEM-GT-benchmarking with PF-AK, CRU, station CSVs).
#                 Observations and CRU under this tree are merged into WIEMIP_ROOT/benchmarking/.
#
#   CONTEXT_DOCS  Folder containing a copy of Cursor Project Library material:
#                 typically `docs/` subtree and `preferences.md`.
#                 Contents are copied into WIEMIP_ROOT/store-notes/ for offline reference.
#
# Standard setup overrides (passed through to setup_wiemip_tem_gt_benchmarking.sh):
#   WIEMIP_ROOT, CRU_TMP_DIR, WIEMIP_GIT_BRANCH, WIEMIP_REPO_URL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup_wiemip_tem_gt_benchmarking.sh"

ROOT="${WIEMIP_ROOT:-/mnt/disks/wiemip-data/TEM-GT-benchmarking}"
BENCHMARKING_DIR="${ROOT}/benchmarking"
STORE_NOTES_DIR="${ROOT}/store-notes"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $*"; }
log_info() { echo -e "${BLUE}[i]${NC} $*"; }

first_existing_dir() {
  local candidate
  for candidate in "$@"; do
    if [[ -n "${candidate}" && -d "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

merge_tree() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [[ ! -d "${src}" ]]; then
    return 1
  fi
  mkdir -p "${dest}"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --info=stats2 "${src}/" "${dest}/"
  else
    cp -a "${src}/." "${dest}/"
  fi
  log_ok "Merged ${label}: ${src} -> ${dest}"
  return 0
}

echo "=========================================="
echo "WIEMIP workstation bootstrap"
echo "=========================================="
log_info "Root: ${ROOT}"
if [[ -n "${MAC_TEM_GT:-}" ]]; then
  log_info "MAC_TEM_GT: ${MAC_TEM_GT}"
else
  log_info "MAC_TEM_GT: (unset — skip Mac data merge)"
fi
if [[ -n "${CONTEXT_DOCS:-}" ]]; then
  log_info "CONTEXT_DOCS: ${CONTEXT_DOCS}"
else
  log_info "CONTEXT_DOCS: (unset — skip Context copy)"
fi
echo ""

if [[ ! -x "${SETUP_SCRIPT}" && ! -f "${SETUP_SCRIPT}" ]]; then
  echo "ERROR: Missing ${SETUP_SCRIPT}" >&2
  exit 1
fi

log_info "Step 1/3: canonical layout and repo (setup_wiemip_tem_gt_benchmarking.sh)"
bash "${SETUP_SCRIPT}"

# --- Optional: merge observations and CRU from Mac staging ---
if [[ -n "${MAC_TEM_GT:-}" ]]; then
  if [[ -d "${MAC_TEM_GT}" ]]; then
    log_info "Step 2/3: merge observations and CRU from MAC_TEM_GT"

  OBS_SRC=""
  if OBS_SRC="$(first_existing_dir \
    "${MAC_TEM_GT}/benchmarking/data/observations" \
    "${MAC_TEM_GT}/data/observations" \
    "${MAC_TEM_GT}/observations" \
    "${MAC_TEM_GT}/benchmarking/observations")"; then
    merge_tree "${OBS_SRC}" "${BENCHMARKING_DIR}/data/observations" "observations"
  else
    log_warn "No observations directory found under MAC_TEM_GT=${MAC_TEM_GT}"
  fi

  CRU_SRC=""
  if CRU_SRC="$(first_existing_dir \
    "${MAC_TEM_GT}/benchmarking/data/climate/CRU" \
    "${MAC_TEM_GT}/data/climate/CRU" \
    "${MAC_TEM_GT}/climate/CRU" \
    "${MAC_TEM_GT}/CRU")"; then
    merge_tree "${CRU_SRC}" "${BENCHMARKING_DIR}/data/climate/CRU" "CRU NetCDF"
  else
    shopt -s nullglob
    nc_files=("${MAC_TEM_GT}"/*.nc)
    shopt -u nullglob
    if [[ ${#nc_files[@]} -gt 0 ]]; then
      mkdir -p "${BENCHMARKING_DIR}/data/climate/CRU"
      for nc in "${nc_files[@]}"; do
        if [[ ! -e "${BENCHMARKING_DIR}/data/climate/CRU/$(basename "${nc}")" ]]; then
          cp -a "${nc}" "${BENCHMARKING_DIR}/data/climate/CRU/"
        fi
      done
      log_ok "Copied CRU *.nc from MAC_TEM_GT root"
    else
      log_warn "No CRU directory or *.nc at MAC_TEM_GT=${MAC_TEM_GT}"
    fi
  fi
  else
    log_warn "MAC_TEM_GT is set but not a directory: ${MAC_TEM_GT}"
  fi
else
  log_info "Step 2/3: skipped (set MAC_TEM_GT after scp to merge PF-AK / station / CRU data)"
fi

# --- Optional: Cursor Context docs into store-notes ---
if [[ -n "${CONTEXT_DOCS:-}" ]]; then
  if [[ -d "${CONTEXT_DOCS}" ]]; then
    log_info "Step 3/3: copy Cursor Context into store-notes"
    mkdir -p "${STORE_NOTES_DIR}"

    if [[ -d "${CONTEXT_DOCS}/docs" ]]; then
      mkdir -p "${STORE_NOTES_DIR}/docs"
      merge_tree "${CONTEXT_DOCS}/docs" "${STORE_NOTES_DIR}/docs" "Context docs/"
    fi

    if [[ -f "${CONTEXT_DOCS}/preferences.md" ]]; then
      cp -f "${CONTEXT_DOCS}/preferences.md" "${STORE_NOTES_DIR}/preferences.md"
      log_ok "Copied preferences.md -> store-notes/"
    fi

    # If user copied the Agent Store root without nesting, merge top-level docs/*.md
    shopt -s nullglob
    for md in "${CONTEXT_DOCS}"/*.md; do
      base="$(basename "${md}")"
      if [[ "${base}" != "preferences.md" ]]; then
        cp -f "${md}" "${STORE_NOTES_DIR}/${base}"
        log_ok "Copied ${base} -> store-notes/"
      fi
    done
    shopt -u nullglob
  else
    log_warn "CONTEXT_DOCS is set but not a directory: ${CONTEXT_DOCS}"
  fi
else
  log_info "Step 3/3: skipped (set CONTEXT_DOCS to copy Project Library docs)"
fi

echo ""
echo "=========================================="
echo "Bootstrap complete — Phase 1 checklist"
echo "=========================================="
echo ""
echo "  [ ] Build DVM-DOS-TEM (wetland/reburn-switch):"
echo "      cd ${BENCHMARKING_DIR}/scripts"
echo "      ./01_setup_model.sh"
echo ""
echo "  [ ] Extract / validate CRU at prototype stations:"
echo "      cd ${BENCHMARKING_DIR}/scripts/download_data"
echo "      python3 download_cru.py --cru-dir ${BENCHMARKING_DIR}/data/climate/CRU \\"
echo "        --stations Deadhorse Imnaviat Smith_Lake_1"
echo ""
echo "  [ ] Run Phase 1 workflow (downloads, inputs, runs, metrics):"
echo "      less ${BENCHMARKING_DIR}/PHASE1_WORKFLOW.md"
echo ""
echo "  Reference:"
echo "    ${BENCHMARKING_DIR}/WIEMIP_BOOTSTRAP.md"
echo "    ${BENCHMARKING_DIR}/WIEMIP_LAYOUT.md"
echo "    ${ROOT}/store-notes/  (Context copies when CONTEXT_DOCS was set)"
echo ""