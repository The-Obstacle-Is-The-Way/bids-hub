# Phase 03: Scripts Reorganization

> Status: Ready after Phase 02
> Blocking: No
> Estimated: 1-2 hours

---

## Goal

Reorganize scripts by dataset namespace for clarity.

---

## Current State (Confusing)

```
scripts/
├── download_arc.sh          # ARC - clear from name
├── validate_download.py     # ARC - NOT clear from name
└── validate_hf_download.py  # ARC - NOT clear from name
```

Problem: `validate_download.py` and `validate_hf_download.py` are ARC-specific but names suggest generic.

---

## Target State (Clear)

```
scripts/
├── arc/
│   ├── download.sh              # Download ARC from OpenNeuro
│   ├── validate_download.py     # Validate local ARC download
│   └── validate_hf_upload.py    # Validate ARC on HuggingFace
│
└── isles24/
    ├── download.sh              # Download ISLES24 from Zenodo
    ├── validate_download.py     # Validate local ISLES24 download
    └── validate_hf_upload.py    # Validate ISLES24 on HuggingFace
```

---

## Implementation Steps

### Step 1: Create Directory Structure

```bash
mkdir -p scripts/arc scripts/isles24
```

### Step 2: Move ARC Scripts

```bash
mv scripts/download_arc.sh scripts/arc/download.sh
mv scripts/validate_download.py scripts/arc/validate_download.py
mv scripts/validate_hf_download.py scripts/arc/validate_hf_upload.py
```

### Step 3: Update ARC Script Internals

**`scripts/arc/download.sh`**
- No changes needed (already ARC-specific)

**`scripts/arc/validate_download.py`**
- Update shebang/docstring to clarify ARC
- Import path unchanged (module handles it)

**`scripts/arc/validate_hf_upload.py`**
- Rename from `validate_hf_download.py` → `validate_hf_upload.py` (clearer)
- Update docstring

### Step 4: Create ISLES24 Scripts

**`scripts/isles24/download.sh`**

```bash
#!/usr/bin/env bash
# Download ISLES24 from Zenodo
# Requires: curl, 7z (p7zip or p7zip-full)
#
# Usage:
#   ./scripts/isles24/download.sh [target_dir]
#
# Default target: data/zenodo/isles24

set -euo pipefail

ZENODO_RECORD="17652035"
ZENODO_URL="https://zenodo.org/records/${ZENODO_RECORD}/files/train.7z"
TARGET_DIR="${1:-data/zenodo/isles24}"

echo "=== ISLES24 Download ==="
echo "Source: Zenodo record ${ZENODO_RECORD}"
echo "Target: ${TARGET_DIR}"
echo ""

# Create target directory
mkdir -p "${TARGET_DIR}"

# Download with resume support
echo "Downloading train.7z (~99GB)..."
curl -L -C - -o "${TARGET_DIR}/train.7z" "${ZENODO_URL}"

# Extract
echo "Extracting..."
7z x "${TARGET_DIR}/train.7z" -o"${TARGET_DIR}/" -y

echo ""
echo "=== Download Complete ==="
echo "Validate with:"
echo "  uv run arc-bids isles24 validate ${TARGET_DIR}/train"
```

**`scripts/isles24/validate_download.py`**

```python
#!/usr/bin/env python3
"""Validate ISLES24 dataset download before HuggingFace upload."""

import sys
from pathlib import Path

from arc_bids.validation import validate_isles24_download

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/isles24/validate_download.py <bids_root>")
        return 1

    bids_root = Path(sys.argv[1])
    result = validate_isles24_download(bids_root)
    print(result.summary())

    return 0 if result.all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
```

**`scripts/isles24/validate_hf_upload.py`**

```python
#!/usr/bin/env python3
"""Validate ISLES24 dataset on HuggingFace after upload.

Performs round-trip validation:
1. Load from HuggingFace
2. Check row count
3. Spot-check NIfTI integrity
"""

import sys
from datasets import load_dataset

HF_REPO = "hugging-science/isles24-stroke"
EXPECTED_SUBJECTS = 149

def main() -> int:
    print(f"Loading {HF_REPO}...")
    ds = load_dataset(HF_REPO, split="train")

    # Check count
    actual = len(ds)
    if actual != EXPECTED_SUBJECTS:
        print(f"ERROR: Expected {EXPECTED_SUBJECTS} subjects, got {actual}")
        return 1

    print(f"Subject count: {actual} ✓")

    # Spot check first row
    example = ds[0]
    required_keys = ["subject_id", "ncct", "dwi", "lesion_mask"]
    for key in required_keys:
        if key not in example:
            print(f"ERROR: Missing key {key}")
            return 1
        if example[key] is None:
            print(f"WARNING: {key} is None for first subject")

    print("Spot check passed ✓")
    print("Validation complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Step 5: Make Scripts Executable

```bash
chmod +x scripts/arc/download.sh
chmod +x scripts/isles24/download.sh
```

### Step 6: Update Documentation

Update any docs that reference old script paths:
- `docs/tutorials/first-upload.md`
- `docs/how-to/validate-before-upload.md`
- `CLAUDE.md`
- `README.md`

---

## Success Criteria

- [ ] `scripts/arc/download.sh` works
- [ ] `scripts/arc/validate_download.py` works
- [ ] `scripts/arc/validate_hf_upload.py` works
- [ ] `scripts/isles24/download.sh` works
- [ ] `scripts/isles24/validate_download.py` works
- [ ] `scripts/isles24/validate_hf_upload.py` works
- [ ] Old script paths removed
- [ ] Docs updated

---

## Next Phase

After scripts reorganization → Phase 04: SRC Reorganization
