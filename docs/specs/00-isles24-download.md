# Phase 00: ISLES24 Download Script

> Status: BLOCKING - Must complete before Phase 01
> Priority: IMMEDIATE

---

## Goal

Create a script to download ISLES24 from Zenodo so we can upload to HuggingFace.

---

## What We Need

**One script:** `scripts/download_isles24.sh`

Downloads the 99GB train.7z from Zenodo and extracts it.

---

## Script Specification

```bash
#!/usr/bin/env bash
# Download ISLES24 from Zenodo
#
# Source: https://zenodo.org/records/17652035
# Size: 99GB compressed
# License: CC BY-NC-SA 4.0
#
# Usage:
#   ./scripts/download_isles24.sh [target_dir]
#
# Default target: data/zenodo/isles24
#
# Requirements:
#   - curl (with resume support)
#   - 7z (p7zip-full on Linux, `brew install p7zip` on macOS)
#   - ~200GB free disk space (99GB compressed + extracted)

set -euo pipefail

ZENODO_RECORD="17652035"
ZENODO_URL="https://zenodo.org/records/${ZENODO_RECORD}/files/train.7z"
TARGET_DIR="${1:-data/zenodo/isles24}"

echo "=== ISLES'24 Download ==="
echo "Source: Zenodo record ${ZENODO_RECORD} (v7, November 2025)"
echo "Target: ${TARGET_DIR}"
echo "Size: ~99GB compressed"
echo ""

# Check for 7z
if ! command -v 7z &> /dev/null; then
    echo "ERROR: 7z not found"
    echo "Install with:"
    echo "  macOS: brew install p7zip"
    echo "  Ubuntu: sudo apt install p7zip-full"
    exit 1
fi

# Create target directory
mkdir -p "${TARGET_DIR}"

# Download with resume support
ARCHIVE="${TARGET_DIR}/train.7z"
if [[ -f "${ARCHIVE}" ]]; then
    echo "Found existing ${ARCHIVE}, resuming download..."
else
    echo "Starting fresh download..."
fi

echo ""
echo "Downloading train.7z (~99GB)..."
echo "(This will take a while. Use Ctrl+C to pause, re-run to resume)"
echo ""

curl -L -C - -o "${ARCHIVE}" "${ZENODO_URL}"

echo ""
echo "Download complete. Verifying..."

# Optional: verify MD5 if we want to be thorough
# Expected: md5:4959a5dd2438d53e3c86d6858484e781
# echo "4959a5dd2438d53e3c86d6858484e781  ${ARCHIVE}" | md5sum -c -

echo ""
echo "Extracting to ${TARGET_DIR}/..."
7z x "${ARCHIVE}" -o"${TARGET_DIR}/" -y

echo ""
echo "=== Download Complete ==="
echo ""
echo "Dataset location: ${TARGET_DIR}/train"
echo ""
echo "Next steps:"
echo "  1. Verify: ls ${TARGET_DIR}/train"
echo "  2. Upload: uv run arc-bids isles24 build ${TARGET_DIR}/train --no-dry-run"
```

---

## Directory Structure After Download

```
data/zenodo/isles24/
├── train.7z              # 99GB compressed archive
└── train/                # Extracted BIDS structure
    ├── raw_data/
    │   └── sub-strokecase0001/
    │       └── ses-0001/
    │           ├── sub-strokecase0001_ses-0001_ncct.nii.gz
    │           ├── sub-strokecase0001_ses-0001_cta.nii.gz
    │           ├── sub-strokecase0001_ses-0001_ctp.nii.gz
    │           └── perfusion-maps/
    │               ├── sub-strokecase0001_ses-0001_tmax.nii.gz
    │               ├── sub-strokecase0001_ses-0001_mtt.nii.gz
    │               ├── sub-strokecase0001_ses-0001_cbf.nii.gz
    │               └── sub-strokecase0001_ses-0001_cbv.nii.gz
    ├── derivatives/
    │   └── sub-strokecase0001/
    │       ├── ses-0001/
    │       │   ├── perfusion-maps/
    │       │   │   ├── sub-strokecase0001_ses-0001_space-ncct_tmax.nii.gz
    │       │   │   ├── sub-strokecase0001_ses-0001_space-ncct_mtt.nii.gz
    │       │   │   ├── sub-strokecase0001_ses-0001_space-ncct_cbf.nii.gz
    │       │   │   └── sub-strokecase0001_ses-0001_space-ncct_cbv.nii.gz
    │       │   ├── sub-strokecase0001_ses-0001_space-ncct_cta.nii.gz
    │       │   ├── sub-strokecase0001_ses-0001_space-ncct_ctp.nii.gz
    │       │   ├── sub-strokecase0001_ses-0001_space-ncct_lvo-msk.nii.gz
    │       │   └── sub-strokecase0001_ses-0001_space-ncct_cow-msk.nii.gz
    │       └── ses-0002/
    │           ├── sub-strokecase0001_ses-02_space-ncct_dwi.nii.gz
    │           ├── sub-strokecase0001_ses-02_space-ncct_adc.nii.gz
    │           └── sub-strokecase0001_ses-02_space-ncct_lesion-msk.nii.gz
    └── phenotype/
        ├── ses-0001/
        │   └── sub-strokecase0001_ses-0001_demographic_baseline.csv
        └── ses-0002/
            └── sub-strokecase0001_ses-0001_outcome.csv
```

---

## Success Criteria

- [ ] Script downloads train.7z from Zenodo
- [ ] Script extracts to target directory
- [ ] 149 subject directories exist in train/raw_data/
- [ ] Can run: `uv run arc-bids isles24 build data/zenodo/isles24/train --dry-run`

---

## Notes

- Download supports resume (curl -C -)
- ~200GB disk space needed (compressed + extracted)
- Can delete train.7z after extraction to save space
- MD5 checksum available for verification: `4959a5dd2438d53e3c86d6858484e781`

---

## Next Phase

After download complete → Phase 01: Upload ISLES24 to HuggingFace
