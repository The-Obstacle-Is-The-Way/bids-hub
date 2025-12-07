# Modular Pipeline Refactor Specification

> Date: 2025-12-07
> Status: **DRAFT** - Needs review before implementation
> Context: arc-aphasia-bids is too ARC-specific, needs generalization

---

## Problem Statement

The current `arc-bids` package is tightly coupled to the ARC dataset. With ISLES24 added,
the codebase is becoming a patchwork of dataset-specific code mixed with generic utilities.

**Current Pain Points:**
1. Package name `arc-bids` is misleading (now handles ISLES24 too)
2. Scripts are ARC-only (`download_arc.sh`, `validate_download.py`)
3. Validation module is ARC-hardcoded (expected counts from Sci Data paper)
4. No ISLES24 download/validation scripts
5. `docs/dataset-cards/` is empty
6. No clear separation between generic and dataset-specific code

---

## Current State Audit

### What's Already Modular (GOOD)

| Component | Location | Why It's Good |
|-----------|----------|---------------|
| `build_hf_dataset()` | `core.py` | Generic, works for any BIDS |
| `push_dataset_to_hub()` | `core.py` | Generic, handles sharding |
| `DatasetBuilderConfig` | `core.py` | Dataset-agnostic dataclass |
| Pattern: `arc.py` / `isles24.py` | `src/arc_bids/` | Clean separation per dataset |

### What's ARC-Hardcoded (BAD)

| Component | Location | Problem |
|-----------|----------|---------|
| `validate_arc_download()` | `validation.py` | Name, expected counts hardcoded |
| `EXPECTED_COUNTS` | `validation.py` | ARC Sci Data paper values only |
| `download_arc.sh` | `scripts/` | No ISLES24 equivalent |
| `validate_download.py` | `scripts/` | Calls `validate_arc_download()` only |
| `validate_hf_download.py` | `scripts/` | Hardcoded to ARC HF repo |
| Package name | `pyproject.toml` | `arc-bids` not general |

### What's Missing

| Component | Needed For |
|-----------|------------|
| `download_isles24.sh` | Download from Zenodo |
| `validate_isles24_download()` | Pre-upload validation |
| `validate_hf_isles24.py` | Round-trip validation |
| Dataset cards | `docs/dataset-cards/{arc,isles24}.md` |
| Generic validation base | Shared `ValidationResult` logic |

---

## Proposed Architecture

### Option 1: Incremental (Recommended)

Keep `arc-bids` name but reorganize internally. Less breaking, faster.

```
src/arc_bids/
├── __init__.py
├── core.py                    # UNCHANGED - generic utilities
├── config.py                  # All dataset configs
├── cli.py                     # CLI with arc/isles24 subcommands
│
├── datasets/                  # NEW: Dataset-specific modules
│   ├── __init__.py
│   ├── arc.py                 # Move from src/arc_bids/arc.py
│   └── isles24.py             # Move from src/arc_bids/isles24.py
│
└── validation/                # NEW: Validation per dataset
    ├── __init__.py
    ├── base.py                # ValidationCheck, ValidationResult (generic)
    ├── arc.py                 # ARC-specific expected counts + checks
    └── isles24.py             # ISLES24-specific expected counts + checks

scripts/
├── download_arc.sh            # EXISTS
├── download_isles24.sh        # NEW
├── validate_download.py       # REFACTOR: add --dataset flag
└── validate_hf_download.py    # REFACTOR: add --dataset flag

docs/
├── dataset-cards/
│   ├── arc-aphasia-bids.md    # NEW: HF dataset card for ARC
│   └── isles24-stroke.md      # NEW: HF dataset card for ISLES24
└── ...existing docs...
```

### Option 2: Full Rename (Future)

Rename package to `bids2hf` or `bids-hf-uploader`. More professional but breaking change.

**Deferred** - do this when we have 3+ datasets.

---

## Implementation Checklist

### Phase 1: Validation Refactor (Priority)

- [ ] Create `src/arc_bids/validation/base.py`
  - Move `ValidationCheck`, `ValidationResult` classes
  - Make them generic (no ARC references)

- [ ] Create `src/arc_bids/validation/arc.py`
  - Move `EXPECTED_COUNTS` and ARC-specific checks
  - Keep `validate_arc_download()` function

- [ ] Create `src/arc_bids/validation/isles24.py`
  - Define `ISLES24_EXPECTED_COUNTS` (149 subjects, etc.)
  - Implement `validate_isles24_download()`

- [ ] Update `src/arc_bids/validation/__init__.py`
  - Re-export for backward compatibility

### Phase 2: Scripts

- [ ] Create `scripts/download_isles24.sh`
  - Zenodo download with curl
  - 7z extraction
  - Resume support

- [ ] Refactor `scripts/validate_download.py`
  - Add `--dataset {arc,isles24}` argument
  - Call appropriate validation function

- [ ] Refactor `scripts/validate_hf_download.py`
  - Add `--dataset {arc,isles24}` argument
  - Parameterize HF repo, expected counts

### Phase 3: Dataset Cards

- [ ] Create `docs/dataset-cards/arc-aphasia-bids.md`
  - Copy from `docs/huggingface-dataset-card.md`
  - This becomes the HF README

- [ ] Create `docs/dataset-cards/isles24-stroke.md`
  - Full attribution to ISLES24 challenge
  - DOI, ArXiv, license info
  - Usage examples with `load_dataset()`

### Phase 4: Module Reorganization (Optional)

- [ ] Create `src/arc_bids/datasets/` directory
- [ ] Move `arc.py` → `datasets/arc.py`
- [ ] Move `isles24.py` → `datasets/isles24.py`
- [ ] Update imports in `cli.py`

---

## ISLES24 Validation Spec

### Expected Counts (from Zenodo v7)

```python
ISLES24_EXPECTED_COUNTS = {
    "subjects": 149,
    "sessions_acute": 149,    # ses-01 (CT/CTA/CTP)
    "sessions_followup": 149,  # ses-02 (DWI/ADC)
    # Raw modalities (ses-01)
    "ncct": 149,
    "cta": 149,
    "ctp": ~140,  # Some subjects missing 4D CTP
    # Perfusion maps (derivatives)
    "tmax": ~140,
    "mtt": ~140,
    "cbf": ~140,
    "cbv": ~140,
    # Follow-up MR (ses-02)
    "dwi": 149,
    "adc": 149,
    # Ground truth
    "lesion_mask": 149,
    "lvo_mask": ~100,  # Optional, not all subjects
    "cow_segmentation": ~100,  # Optional
}
```

### Required BIDS Files

```python
ISLES24_REQUIRED_FILES = [
    "participants.tsv",
    # dataset_description.json may not exist - BIDS-ish not strict BIDS
]
```

### Validation Function Signature

```python
def validate_isles24_download(
    bids_root: Path,
    nifti_sample_size: int = 10,
    tolerance: float = 0.1,  # 10% tolerance for optional modalities
) -> ValidationResult:
    """Validate ISLES24 dataset download from Zenodo."""
    ...
```

---

## Download Script Spec

### `scripts/download_isles24.sh`

```bash
#!/usr/bin/env bash
# Download ISLES24 from Zenodo (99GB)
# Requires: curl, 7z (p7zip)

ZENODO_URL="https://zenodo.org/records/17652035/files/train.7z"
TARGET_DIR="${1:-data/zenodo/isles24}"

# Download with resume support
curl -L -C - -o "$TARGET_DIR/train.7z" "$ZENODO_URL"

# Extract
7z x "$TARGET_DIR/train.7z" -o"$TARGET_DIR/"

# Verify
echo "Download complete. Verify with:"
echo "  arc-bids isles24 validate $TARGET_DIR/train"
```

---

## CLI Updates

Current CLI:
```
arc-bids build ...          # ARC
arc-bids isles24 build ...  # ISLES24
arc-bids validate ...       # ARC only!
```

Proposed CLI:
```
arc-bids arc build ...
arc-bids arc validate ...
arc-bids isles24 build ...
arc-bids isles24 validate ...  # NEW
arc-bids info                  # Show both datasets
```

Or keep backward compatibility:
```
arc-bids build ...           # ARC (legacy)
arc-bids validate ...        # ARC (legacy)
arc-bids isles24 build ...
arc-bids isles24 validate ...  # NEW
```

---

## Priority Order

1. **ISLES24 validation** - Need this before upload
2. **Download script** - Document the process
3. **Dataset cards** - Required for HF upload
4. **Module reorganization** - Nice to have, not blocking

---

## Questions to Resolve

1. **CLI structure**: Keep `build`/`validate` at top level for ARC backward compat?
2. **Package rename**: Defer until we have 3+ datasets?
3. **Validation tolerance**: 10% for optional modalities?

---

## Related

- ISLES24 upload spec: `_burner/docs/isles24-full-upload-spec.md`
- Current validation: `src/arc_bids/validation.py`
- Existing scripts: `scripts/`
