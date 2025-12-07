# Phase 01: Upload ISLES24 to HuggingFace

> Status: **PRIORITY** - Do this BEFORE any refactoring
> Blocking: Yes - This is the immediate deliverable
> Estimated: 1-2 hours after download completes

---

## Goal

Upload ISLES24 dataset to `hugging-science/isles24-stroke` using existing code.

**No refactoring required.** The current `isles24.py` module is complete.

---

## Prerequisites

- [ ] Download complete (99GB from Zenodo)
- [ ] Verify extraction completed successfully
- [ ] HuggingFace authentication (`huggingface-cli login`)

---

## Steps

### 1. Verify Download Structure

```bash
# Check the extracted structure
ls -la data/zenodo/isles24/

# Expected:
# train/
#   ├── participants.tsv
#   ├── rawdata/
#   │   └── sub-strokeXXXX/
#   │       ├── ses-01/  (CT/CTA/CTP)
#   │       └── ses-02/  (DWI/ADC)
#   └── derivatives/
#       ├── perfusion_maps/
#       ├── lesion_masks/
#       ├── lvo_masks/
#       └── cow_segmentations/
```

### 2. Quick Validation (Manual)

```bash
# Count subjects
ls data/zenodo/isles24/train/rawdata/ | wc -l
# Expected: 149

# Check participants.tsv exists
cat data/zenodo/isles24/train/participants.tsv | head -5

# Spot check a subject
ls -la data/zenodo/isles24/train/rawdata/sub-stroke0001/
```

### 3. Dry Run Build

```bash
uv run arc-bids isles24 build data/zenodo/isles24/train --dry-run
```

Expected output:
- "Found 149 subjects"
- "Dry run complete. Dataset built but not pushed."

### 4. Actual Upload

```bash
# This will take a while (149 shards, each ~500MB-1GB)
uv run arc-bids isles24 build data/zenodo/isles24/train --no-dry-run
```

### 5. Verify Upload

```python
from datasets import load_dataset

ds = load_dataset("hugging-science/isles24-stroke", split="train", streaming=True)
example = next(iter(ds))
print(example.keys())
# Should show: subject_id, ncct, cta, ctp, tmax, mtt, cbf, cbv, dwi, adc, lesion_mask, etc.
```

---

## If Structure Differs from Expected

The `isles24.py` module was written based on the expected Zenodo structure. If the actual
structure differs:

1. **Inspect actual structure:**
   ```bash
   find data/zenodo/isles24/train -type d | head -50
   find data/zenodo/isles24/train -name "*.nii.gz" | head -20
   ```

2. **Update `build_isles24_file_table()` in `src/arc_bids/isles24.py`:**
   - Adjust directory paths
   - Adjust glob patterns
   - Test with dry run

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
