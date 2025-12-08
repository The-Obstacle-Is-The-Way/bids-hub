# Phase 01: Upload ISLES24 to HuggingFace

> Status: **PRIORITY** - Do this BEFORE any refactoring
> Blocking: Yes - This is the immediate deliverable

---

## Goal

Upload ISLES24 dataset to `hugging-science/isles24-stroke` using the updated `isles24.py` module.

**Note:** The `isles24.py` module must be updated to match the actual Zenodo v7 structure before upload.

---

## Prerequisites

- [ ] Download complete (99GB from Zenodo)
- [ ] Verify extraction completed successfully
- [ ] `isles24.py` updated to match actual Zenodo v7 structure
- [ ] HuggingFace authentication (`huggingface-cli login`)

---

## Steps

### 1. Verify Download Structure

```bash
# Check the extracted structure
ls -la data/zenodo/isles24/train/

# Expected (actual Zenodo v7):
# clinical_data-description.xlsx
# raw_data/
# derivatives/
# phenotype/

# Count subjects
ls data/zenodo/isles24/train/raw_data/ | wc -l
# Expected: 149

# Verify subject naming
ls data/zenodo/isles24/train/raw_data/ | head -3
# Expected: sub-stroke0001, sub-stroke0002, sub-stroke0003

# Verify session naming
ls data/zenodo/isles24/train/raw_data/sub-stroke0001/
# Expected: ses-01 (NOT ses-0001!)

# Check derivative structure
ls data/zenodo/isles24/train/derivatives/sub-stroke0001/
# Expected: ses-01, ses-02

# Verify filename pattern
ls data/zenodo/isles24/train/derivatives/sub-stroke0001/ses-01/
# Expected: *_space-ncct_*.nii.gz files
```

### 2. Dry Run Build

```bash
uv run arc-bids isles24 build data/zenodo/isles24/train --dry-run
```

Expected output:
- "Found 149 subjects"
- "Dry run complete. Dataset built but not pushed."

### 3. Actual Upload

```bash
# This will take a while (149 shards, each ~500MB-1GB)
uv run arc-bids isles24 build data/zenodo/isles24/train --no-dry-run
```

### 4. Verify Upload

```python
from datasets import load_dataset

ds = load_dataset("hugging-science/isles24-stroke", split="train", streaming=True)
example = next(iter(ds))
print(example.keys())
# Should show: subject_id, ncct, cta, ctp, tmax, mtt, cbf, cbv, dwi, adc, lesion_mask, etc.
```

---

## Zenodo v7 Structure Reference

**This is the SSOT** - code must match this exactly:

```
train/
├── clinical_data-description.xlsx    # Metadata file (NOT participants.tsv!)
├── raw_data/                         # NOTE: raw_data (with underscore)
│   └── sub-stroke0001/               # Subject ID pattern
│       └── ses-01/                   # Session: ses-01, ses-02 (NOT ses-0001!)
│           ├── sub-stroke0001_ses-01_ncct.nii.gz
│           ├── sub-stroke0001_ses-01_cta.nii.gz
│           ├── sub-stroke0001_ses-01_ctp.nii.gz
│           └── perfusion-maps/
│               └── sub-stroke0001_ses-01_*.nii.gz
├── derivatives/
│   └── sub-stroke0001/               # Per-subject (NOT per-derivative-type!)
│       ├── ses-01/
│       │   ├── perfusion-maps/
│       │   │   └── sub-stroke0001_ses-01_space-ncct_tmax.nii.gz  # lowercase!
│       │   ├── sub-stroke0001_ses-01_space-ncct_cta.nii.gz
│       │   ├── sub-stroke0001_ses-01_space-ncct_ctp.nii.gz
│       │   ├── sub-stroke0001_ses-01_space-ncct_lvo-msk.nii.gz
│       │   └── sub-stroke0001_ses-01_space-ncct_cow-msk.nii.gz
│       └── ses-02/
│           ├── sub-stroke0001_ses-02_space-ncct_dwi.nii.gz
│           ├── sub-stroke0001_ses-02_space-ncct_adc.nii.gz
│           └── sub-stroke0001_ses-02_space-ncct_lesion-msk.nii.gz
└── phenotype/
    └── sub-stroke0001/
        ├── ses-01/
        └── ses-02/
```

---

## Required Code Changes in isles24.py

The following must be updated to match Zenodo v7:

| Line | Current | Should Be |
|------|---------|-----------|
| ~97 | `rawdata_root = bids_root / "rawdata"` | `raw_data_root = bids_root / "raw_data"` |
| ~103 | `participants_tsv = bids_root / "participants.tsv"` | Parse `clinical_data-description.xlsx` or phenotype/ |
| ~121 | `ses01_dir = subject_dir / "ses-01"` | Correct (but verify) |
| ~124 | `ses01_dir / "ct"` | `ses01_dir` (flat, no ct/ subdir) |
| ~130 | `derivatives/perfusion_maps/sub-X/...` | `derivatives/sub-X/ses-01/perfusion-maps/` |
| ~131 | `*_Tmax.nii.gz` | `*_space-ncct_tmax.nii.gz` |
| ~148 | `derivatives/lesion_masks/sub-X/...` | `derivatives/sub-X/ses-02/` |

---

## Success Criteria

- [ ] Dataset visible at https://huggingface.co/datasets/hugging-science/isles24-stroke
- [ ] Dataset Viewer shows sample data
- [ ] `load_dataset()` works in Python
- [ ] 149 subjects uploaded
- [ ] All modalities present (ncct, cta, ctp, dwi, adc, lesion_mask, etc.)

---

## Rollback

If upload fails partway:
```bash
# Delete partial upload
huggingface-cli repo delete hugging-science/isles24-stroke --repo-type dataset -y

# Fix issues and retry
```

---

## Next Phase

After successful upload → Phase 02: Validation Refactor
