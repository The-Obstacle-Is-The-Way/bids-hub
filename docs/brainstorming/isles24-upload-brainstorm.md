# ISLES24 Proper Upload Brainstorm

> Date: 2025-12-07
> Context: stroke-deepisles-demo needs proper HF dataset, not ZIP garbage

## The Problem

**Current state of ISLES24-MR-Lite on HuggingFace:**
- URL: https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite
- Format: Raw NIfTI files dumped (not proper HF Dataset)
- Dataset Viewer: "heuristics could not detect any supported data files"
- Size: 149 cases (~1-2 GB)
- License: CC BY-NC 4.0

**Why this sucks:**
- `load_dataset()` doesn't work
- No streaming support
- No Dataset Viewer integration
- Forces workarounds (download ZIPs, extract locally, bake into Docker)

## What We Have

**arc-aphasia-bids pipeline:**
- Successfully uploaded 293 GB ARC dataset
- Proper parquet format with `Nifti()` feature types
- Works with `load_dataset()` + NiiVue viewer
- One row per session design

**ISLES24 data structure (after extraction):**
```
data/isles24/
├── Images-DWI/sub-stroke{XXXX}_ses-02_dwi.nii.gz        # 149 files
├── Images-ADC/sub-stroke{XXXX}_ses-02_adc.nii.gz        # 149 files
└── Masks/sub-stroke{XXXX}_ses-02_lesion-msk.nii.gz      # 149 files
```

## The Math

| Dataset | Size | Effort to Upload |
|---------|------|------------------|
| ARC Aphasia | 293 GB | Already done |
| ISLES24 | ~1-2 GB | Trivial in comparison |

If our pipeline handles 293 GB, it can handle 1-2 GB in minutes.

## Decision: Just Do It Properly

**Why:**
1. Pipeline already exists and works
2. ISLES24 is <1% the size of ARC
3. Avoids Docker image bloat (baking data in)
4. Faster cold starts on HF Spaces
5. Dataset versioning without redeploy
6. Other users can use the dataset in their projects
7. Proper streaming/caching support

**The alternative (bake into Docker):**
- Not that bad for a few gigs
- But why add technical debt when we have the tooling?
- Would need to migrate later anyway

## Schema Comparison

**ARC (what we have):**
```python
Features({
    "subject_id": Value("string"),
    "session_id": Value("string"),
    "t1w": Nifti(),
    "t2w": Nifti(),
    "flair": Nifti(),
    "bold": Nifti(),
    "dwi": Nifti(),
    "sbref": Nifti(),
    "lesion": Nifti(),
    # ... metadata
})
```

**ISLES24 (what we need):**
```python
Features({
    "subject_id": Value("string"),       # e.g., "sub-stroke0001"
    "session_id": Value("string"),       # "ses-02" (all same session)
    "dwi": Nifti(),                       # Diffusion-weighted imaging
    "adc": Nifti(),                       # Apparent diffusion coefficient
    "lesion_mask": Nifti(),               # Ground truth segmentation
})
```

Much simpler schema - only 3 NIfTI columns vs 7.

## Full ISLES 2024 vs MR-Lite Subset

**ISLES24-MR-Lite (what's on HF now):**
- 149 MR cases (DWI + ADC + masks)
- Subset of full challenge data

**Full ISLES 2024 (on Grand Challenge):**
- 245 total cases
- Training: 150 cases
- Test: ~95 cases (held out for challenge)
- Includes CT data (NCCT, CTP, CTA) + MR data
- Requires Grand Challenge registration

**Should we upload the full one?**
- For stroke-deepisles-demo: MR-Lite subset is sufficient (DeepISLES uses DWI+ADC)
- Full dataset includes CT which DeepISLES doesn't use
- MR-Lite already has what we need

**Recommendation:** Upload MR-Lite properly first. Full dataset is overkill for this demo.

## Action Plan

1. **Download ISLES24-MR-Lite** (or use existing local extraction)
   ```bash
   huggingface-cli download YongchengYAO/ISLES24-MR-Lite --local-dir data/isles24
   ```

2. **Adapt arc-aphasia-bids pipeline** for ISLES24 schema
   - Simpler schema (3 NIfTI columns)
   - BIDS-like naming already present

3. **Upload to new HF repo**
   - `hugging-science/isles24-stroke` or similar
   - Proper parquet format with `Nifti()` features

4. **Update stroke-deepisles-demo** to use proper dataset
   - Implement the HuggingFace mode in `loader.py`
   - Remove baked-in data from Docker image

## Links

- Current garbage upload: https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite
- Full challenge: https://isles-24.grand-challenge.org/
- Our working pipeline: https://github.com/The-Obstacle-Is-The-Way/arc-aphasia-bids
- Our working dataset: https://huggingface.co/datasets/hugging-science/arc-aphasia-bids
- Zenodo reference: https://zenodo.org/records/10991145
- ArXiv paper: https://arxiv.org/abs/2408.11142

## Bottom Line

We have production tooling. ISLES24 is tiny. Just do it right.
The "shortcut" of baking data into Docker isn't even faster given we already have the pipeline.
