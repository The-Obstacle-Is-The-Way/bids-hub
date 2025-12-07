# ISLES'24 Full Dataset Upload Specification

> Date: 2025-12-07
> Status: **APPROVED** - Audit validated, ready for implementation
> Context: Extending arc-aphasia-bids pipeline to upload ISLES'24 properly

---

## Audit Validation Summary

| Audit Claim | Validated? | Notes |
|-------------|------------|-------|
| Flattened schema (subject-level) | ✅ TRUE | ML task is input→output, not longitudinal |
| num_shards=149 | ✅ TRUE | Same pattern as ARC, ~664MB per shard |
| Keep datasets git pin | ✅ TRUE | Safe default, no harm |
| Add py7zr | ❌ NOT NEEDED | CLI `7z` already installed |
| HF Viewer won't work | ✅ TRUE | Expected for `Nifti()` types |
| Remove session_id | ✅ TRUE | Columns indicate source session |

---

## Executive Summary

We have a production pipeline (`arc-aphasia-bids`) that successfully uploaded 293GB of BIDS
neuroimaging data to HuggingFace. The ISLES'24 dataset (99GB) is currently:
- **Full dataset**: Only on Zenodo as a `.7z` archive
- **MR-Lite subset**: On HuggingFace as garbage (raw files, no `load_dataset()` support)

**Proposal**: Upload the full ISLES'24 training set properly to HuggingFace, proving our
pipeline is a general-purpose BIDS→HF converter.

---

## Data Sources

### 1. Full ISLES'24 Training Set (Zenodo)

| Field | Value |
|-------|-------|
| URL | https://zenodo.org/records/17652035 |
| DOI | 10.5281/zenodo.17652035 |
| Version | v7 (Nov 20, 2025) - LATEST |
| Size | ~99 GB (compressed `.7z`) |
| Cases | 149 acute ischemic stroke patients |
| License | CC BY-NC-SA 4.0 |

**Contents:**
```
train/
├── rawdata/
│   ├── sub-strokeXXXX/
│   │   ├── ses-01/           # Admission (acute)
│   │   │   ├── ct/           # Non-contrast CT
│   │   │   ├── cta/          # CT Angiography
│   │   │   └── ctp/          # CT Perfusion (4D)
│   │   └── ses-02/           # Follow-up (2-9 days)
│   │       └── dwi/          # DWI + ADC
│   └── ...
├── derivatives/
│   ├── perfusion_maps/       # tmax, mtt, cbf, cbv
│   ├── lesion_masks/         # Ground truth infarct
│   ├── lvo_masks/            # Large vessel occlusion
│   └── cow_segmentations/    # Circle of Willis
└── participants.tsv          # Clinical metadata
```

**Modalities:**
- Admission CT: NCCT, CTA, 4D CTP
- Perfusion maps: Tmax, MTT, CBF, CBV
- Follow-up MR: DWI, ADC
- Masks: Lesion, LVO, CoW

### 2. ISLES24-MR-Lite Subset (Current HF Garbage)

| Field | Value |
|-------|-------|
| URL | https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite |
| Size | ~1-2 GB |
| Cases | 149 (same patients, MR only) |
| License | CC BY-NC 4.0 |
| Format | Raw NIfTI files (NOT proper HF Dataset) |

**Why it sucks:**
- Dataset Viewer says "heuristics could not detect any supported data files"
- No parquet format
- No `Nifti()` feature types
- `load_dataset()` doesn't work
- Forces workarounds (bake into Docker, etc.)

---

## Decision: Upload FULL Dataset

**Why full instead of just MR-Lite?**

1. **Completeness**: DeepISLES uses DWI+ADC, but other models use CT/CTP
2. **Scientific value**: Full multimodal dataset enables more research
3. **Proof of pipeline**: 99GB is still less than ARC (293GB)
4. **No extra effort**: Same pipeline, just different schema
5. **Community benefit**: Properly uploaded = everyone can use it

**Why we're allowed:**
- License: CC BY-NC-SA 4.0 allows redistribution with attribution
- Etiquette: Just repackaging for easier ML use (standard practice)
- Credit: Full citations + DOIs in README

---

## Pipeline Architecture

### Current State (arc-aphasia-bids)

```
src/arc_bids/
├── __init__.py
├── config.py      # BidsDatasetConfig, ARC_CONFIG
├── core.py        # GENERIC: build_hf_dataset(), push_dataset_to_hub()
├── arc.py         # ARC-SPECIFIC: build_arc_file_table(), get_arc_features()
├── cli.py         # Typer CLI
└── validation.py  # ARC-specific validation
```

**Key insight**: `core.py` is already generic! The dataset-specific logic lives in:
- `build_*_file_table()` - walks BIDS structure → DataFrame
- `get_*_features()` - returns Features schema

### Proposed Extension

```
src/arc_bids/
├── config.py      # Add ISLES24_CONFIG
├── core.py        # No changes needed
├── arc.py         # Unchanged
├── isles24.py     # NEW: build_isles24_file_table(), get_isles24_features()
├── cli.py         # Add `isles24` subcommand
└── validation.py  # Optionally add ISLES24 validation
```

---

## Schema Design

### Decision: FLATTENED (One Row Per Subject)

**Why flattened, not session-per-row like ARC?**

| Dataset | Structure | Reason for Schema Choice |
|---------|-----------|--------------------------|
| ARC | 230 subjects × ~4 sessions = 902 rows | Longitudinal study, sessions are independent |
| ISLES24 | 149 subjects × 2 sessions = 149 rows | ML task is `acute → outcome`, sessions are paired |

The ISLES24 ML task is: **Acute CT at admission → Predict final infarct on follow-up MR**

Having data in separate rows would force users to join them. Flattening keeps input→target in same row.

### ISLES'24 Final Schema

```python
from datasets import Features, Nifti, Value

def get_isles24_features() -> Features:
    """
    Flattened schema: one row per subject with all modalities.

    Note: No session_id column - modality names indicate source:
    - CT/CTA/CTP/perfusion maps = acute admission (ses-01)
    - DWI/ADC/lesion = follow-up (ses-02)
    """
    return Features({
        # Identifier (no session_id - flattened)
        "subject_id": Value("string"),        # e.g., "sub-stroke0001"

        # === ACUTE ADMISSION (ses-01) ===
        # Raw CT
        "ncct": Nifti(),                      # Non-contrast CT
        "cta": Nifti(),                       # CT Angiography
        "ctp": Nifti(),                       # 4D CT Perfusion (nullable)

        # Perfusion maps (derivatives)
        "tmax": Nifti(),                      # Time to max
        "mtt": Nifti(),                       # Mean transit time
        "cbf": Nifti(),                       # Cerebral blood flow
        "cbv": Nifti(),                       # Cerebral blood volume

        # === FOLLOW-UP (ses-02) ===
        # MR imaging
        "dwi": Nifti(),                       # Diffusion-weighted imaging
        "adc": Nifti(),                       # Apparent diffusion coefficient

        # === GROUND TRUTH (derivatives) ===
        "lesion_mask": Nifti(),               # Final infarct segmentation
        "lvo_mask": Nifti(),                  # Large vessel occlusion (nullable)
        "cow_segmentation": Nifti(),          # Circle of Willis (nullable)

        # === CLINICAL METADATA ===
        "age": Value("float32"),
        "sex": Value("string"),
        "nihss_admission": Value("float32"),  # Stroke severity at admission
        "mrs_3month": Value("float32"),       # Functional outcome at 3 months
        "thrombolysis": Value("string"),      # IVT treatment (Yes/No)
        "thrombectomy": Value("string"),      # EVT treatment (Yes/No)
        # ... other clinical fields TBD after inspecting participants.tsv
    })
```

### Why No `Sequence(Nifti())`?

ARC uses `Sequence(Nifti())` for `bold`, `dwi`, `sbref` because there can be **multiple runs per session**.

ISLES24 has **one file per modality per subject**. No sequences needed. This also avoids the
`datasets` bug (#7894) that affects `Sequence(Nifti())` after sharding.

### HuggingFace Dataset Viewer Limitation

**Expected behavior**: The HF Dataset Viewer will show an error like "ConfigNamesError" or
"heuristics could not detect any supported data files".

**This is normal** for datasets with custom feature types like `Nifti()`. Users must use
`load_dataset()` programmatically. Document this in the README.

---

## Download Strategy

### Direct Zenodo Download (RECOMMENDED)

```bash
# Download train.7z (~99GB) - v7 LATEST
# Use -C - for resume support if interrupted
cd /path/to/arc-aphasia-bids/data/zenodo/isles24

curl -L -C - -o train.7z 'https://zenodo.org/records/17652035/files/train.7z?download=1'

# Or with wget
wget -c https://zenodo.org/records/17652035/files/train.7z
```

### Extract with 7z

```bash
# Extract (requires p7zip: brew install p7zip)
7z x train.7z -o./

# Result: ./train/ directory with BIDS structure
```

### Resume Support

Both `curl -C -` and `wget -c` support resuming interrupted downloads.
The download is ~99GB, expect 2-3 hours depending on connection.

---

## Local Data Directory

Current:
```
data/
└── openneuro/
    └── ds004884/          # ARC dataset (293GB when downloaded)
```

Proposed:
```
data/
├── openneuro/
│   └── ds004884/          # ARC (existing)
└── zenodo/
    └── isles24/
        ├── train.7z       # Downloaded archive (99GB)
        └── train/         # Extracted BIDS data
```

Both are gitignored (data/ is in .gitignore).

---

## HuggingFace Repository

| Field | Value |
|-------|-------|
| Proposed repo | `hugging-science/isles24-stroke` |
| License | CC BY-NC-SA 4.0 (same as source) |
| Tags | medical, stroke, neuroimaging, BIDS, CT, MRI, segmentation |

**README must include:**
- Full attribution to ISLES'24 challenge organizers
- DOI: 10.5281/zenodo.17652035 (v7 - latest)
- ArXiv: 2408.11142
- License notice
- Citation instructions

---

## Implementation Checklist

### Phase 1: Data Acquisition
- [x] Download `train.7z` from Zenodo (~99GB) - **IN PROGRESS via tmux**
- [ ] Extract to `data/zenodo/isles24/train/` using `7z x train.7z`
- [ ] Inspect BIDS structure (verify expected layout)
- [ ] Inspect `participants.tsv` for clinical fields

### Phase 2: Schema Definition
- [x] Decide: one row per subject (FLATTENED) - **DECIDED**
- [ ] Finalize `get_isles24_features()` based on actual structure (verify after extraction)
- [ ] Create `src/arc_bids/isles24.py`

### Phase 3: File Table Builder
- [ ] Implement `build_isles24_file_table()`
- [ ] Handle both CT (ses-01) and MR (ses-02) modalities
- [ ] Map derivatives (perfusion maps, masks)
- [ ] Extract clinical metadata

### Phase 4: CLI Integration
- [ ] Add `isles24` subcommand to CLI
- [ ] Add `ISLES24_CONFIG` to config.py

### Phase 5: Upload
- [ ] Dry run: `uv run arc-bids isles24 build data/zenodo/isles24/train --dry-run`
- [ ] Create HF repo: `hugging-science/isles24-stroke`
- [ ] Full upload with sharding

### Phase 6: Validation
- [ ] Test `load_dataset("hugging-science/isles24-stroke")`
- [ ] Verify Dataset Viewer shows expected error (custom type)
- [ ] Update stroke-deepisles-demo to use new dataset

---

## Naming Considerations

Current package name: `arc-bids`

**Problem**: Too specific. Should be generic like `hf-bids-pipeline` or `bids2hf`.

**Options:**
1. Keep `arc-bids`, add ISLES24 as second dataset (pragmatic)
2. Rename package to `bids-hf-uploader` or similar (breaking change)
3. Fork to new repo with generic name (duplication)

**Recommendation**: Option 1 for now. Rename is a separate task.

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Download takes forever | Background download via tmux, resume support via curl -C - |
| Schema mismatch | Inspect actual BIDS structure after extraction before coding |
| 99GB upload fails | Existing sharding logic handles this (proven with 293GB ARC) |
| License issues | CC BY-NC-SA explicitly allows redistribution with attribution |

---

## Questions for Senior Review (RESOLVED)

1. **Full vs MR-only?** ✅ RESOLVED
   - **Decision**: Full dataset (99GB)
   - **Rationale**: More useful for community, same effort, proves pipeline generality

2. **Schema design?** ✅ RESOLVED
   - **Decision**: Flattened (one row per subject)
   - **Rationale**: ML task is `acute → outcome`, sessions are paired not independent
   - **Bonus**: Avoids `Sequence(Nifti())` bug

3. **Package naming?** ✅ RESOLVED (DEFERRED)
   - **Decision**: Keep `arc-bids` for now, add isles24 module
   - **Rationale**: Rename is breaking change, do separately

4. **Priority?** ✅ RESOLVED
   - **Decision**: Upload ISLES24 properly, then update stroke-deepisles-demo
   - **Rationale**: Clean HF dataset enables seamless `load_dataset()`, no Docker baking

5. **Dependencies?** ✅ RESOLVED
   - **Decision**: Keep `datasets` git pin (safe default)
   - **Rationale**: Even though ISLES24 won't use `Sequence(Nifti())`, pin is harmless

6. **Extraction?** ✅ RESOLVED
   - **Decision**: Use CLI `7z` (already installed via homebrew)
   - **Rationale**: No need for py7zr Python dependency

---

## Links

- ISLES'24 Challenge: https://isles-24.grand-challenge.org/
- Zenodo (full data, v7): https://zenodo.org/records/17652035
- HF garbage upload: https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite
- ArXiv paper: https://arxiv.org/abs/2408.11142
- Our ARC pipeline: https://github.com/The-Obstacle-Is-The-Way/arc-aphasia-bids
- Our ARC dataset: https://huggingface.co/datasets/hugging-science/arc-aphasia-bids
- stroke-deepisles-demo: https://github.com/The-Obstacle-Is-The-Way/stroke-deepisles-demo
