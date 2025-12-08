# Phase 05: Documentation Cleanup

> Status: Ready after Phase 04
> Blocking: No
> Estimated: 2-3 hours

---

## Goal

1. Create dataset cards for HuggingFace
2. Update existing docs to reflect multi-dataset support
3. Clean up stale/redundant documentation

---

## Current State

```
docs/
├── dataset-cards/           # EMPTY ❌
├── explanation/
│   ├── architecture.md
│   └── why-uploads-fail.md
├── how-to/
│   ├── fix-empty-uploads.md
│   ├── fix-upload-crashes.md
│   ├── validate-before-upload.md
│   └── validate-download-from-hub.md
├── reference/
│   ├── api.md
│   ├── cli.md
│   └── schema.md
├── tutorials/
│   └── first-upload.md
├── huggingface-dataset-card.md  # ARC card (should move)
└── index.md
```

---

## Target State

```
docs/
├── dataset-cards/
│   ├── arc-aphasia-bids.md      # ARC HuggingFace README
│   └── isles24-stroke.md        # ISLES24 HuggingFace README
├── explanation/
│   ├── architecture.md          # Update for multi-dataset
│   └── why-uploads-fail.md
├── how-to/
│   ├── fix-empty-uploads.md
│   ├── fix-upload-crashes.md
│   ├── validate-before-upload.md
│   └── validate-download-from-hub.md
├── reference/
│   ├── api.md                   # Update for new module structure
│   ├── cli.md                   # Update for isles24 commands
│   └── schema.md                # Add ISLES24 schema
├── tutorials/
│   ├── upload-arc.md            # Rename from first-upload.md
│   └── upload-isles24.md        # NEW
└── index.md                     # Update overview
```

---

## Implementation Steps

### Step 1: Create Dataset Cards

**`docs/dataset-cards/arc-aphasia-bids.md`**

```markdown
---
license: cc0-1.0
task_categories:
  - image-segmentation
  - image-classification
tags:
  - medical
  - neuroimaging
  - stroke
  - aphasia
  - MRI
  - BIDS
size_categories:
  - 100K<n<1M
---

# Aphasia Recovery Cohort (ARC) Dataset

Multimodal neuroimaging dataset of 230 chronic stroke patients with aphasia.

## Dataset Description

- **Source:** [OpenNeuro ds004884](https://openneuro.org/datasets/ds004884)
- **Paper:** [Gibson et al., Scientific Data 2024](https://doi.org/10.1038/s41597-024-03819-7)
- **License:** CC0 (Public Domain)

## Dataset Structure

| Modality | Count | Description |
|----------|-------|-------------|
| T1w | 441 | T1-weighted structural MRI |
| T2w | 447 | T2-weighted structural MRI |
| FLAIR | 235 | Fluid-attenuated inversion recovery |
| BOLD | 850 | Functional MRI |
| DWI | 613 | Diffusion-weighted imaging |
| Lesion Masks | 230 | Expert-drawn stroke lesion segmentations |

## Usage

\`\`\`python
from datasets import load_dataset

ds = load_dataset("hugging-science/arc-aphasia-bids", split="train")

# Access a subject
example = ds[0]
print(example["subject_id"])  # "sub-M2001"
print(example["t1w"])         # NIfTI array
print(example["wab_aq"])      # Aphasia severity score
\`\`\`

## Citation

\`\`\`bibtex
@article{gibson2024arc,
  title={A large open access dataset of brain MRI and behaviour...},
  author={Gibson, Erin and others},
  journal={Scientific Data},
  year={2024}
}
\`\`\`
```

**`docs/dataset-cards/isles24-stroke.md`**

```markdown
---
license: cc-by-nc-sa-4.0
task_categories:
  - image-segmentation
tags:
  - medical
  - neuroimaging
  - stroke
  - CT
  - MRI
  - perfusion
  - ISLES
size_categories:
  - 1K<n<10K
---

# ISLES 2024 Stroke Dataset

Multimodal acute stroke imaging dataset from the ISLES 2024 Challenge.

## Dataset Description

- **Source:** [Zenodo Record 17652035](https://zenodo.org/records/17652035)
- **Challenge:** [ISLES 2024](https://isles-24.grand-challenge.org/)
- **License:** CC BY-NC-SA 4.0

## Dataset Structure

149 subjects with acute stroke imaging:

| Session | Modality | Description |
|---------|----------|-------------|
| ses-01 (Acute) | NCCT | Non-contrast CT |
| ses-01 (Acute) | CTA | CT Angiography |
| ses-01 (Acute) | CTP | CT Perfusion (4D) |
| ses-01 (Acute) | Tmax, MTT, CBF, CBV | Perfusion maps |
| ses-02 (Follow-up) | DWI | Diffusion-weighted MRI |
| ses-02 (Follow-up) | ADC | Apparent diffusion coefficient |
| Derivatives | Lesion Mask | Ground truth segmentation |

## Usage

\`\`\`python
from datasets import load_dataset

ds = load_dataset("hugging-science/isles24-stroke", split="train")

# Access a subject
example = ds[0]
print(example["subject_id"])    # "sub-stroke0001"
print(example["ncct"])          # CT array
print(example["lesion_mask"])   # Segmentation mask
print(example["nihss_admission"])  # Stroke severity
\`\`\`

## Citation

\`\`\`bibtex
@article{isles2024,
  title={ISLES 2024: Ischemic Stroke Lesion Segmentation Challenge},
  author={ISLES Organizers},
  year={2024}
}
\`\`\`
```

### Step 2: Move Existing Dataset Card

```bash
mv docs/huggingface-dataset-card.md docs/dataset-cards/arc-aphasia-bids.md
```

(Then update content as shown above)

### Step 3: Update Index

**`docs/index.md`**

```markdown
# bids-hub Documentation

Upload BIDS neuroimaging datasets to HuggingFace Hub.

## Supported Datasets

| Dataset | HuggingFace Repo | Size |
|---------|------------------|------|
| ARC (Aphasia Recovery Cohort) | [hugging-science/arc-aphasia-bids](https://hf.co/datasets/hugging-science/arc-aphasia-bids) | 293 GB |
| ISLES 2024 | [hugging-science/isles24-stroke](https://hf.co/datasets/hugging-science/isles24-stroke) | ~100 GB |

## Quick Start

### ARC Dataset
\`\`\`bash
# Download
./scripts/arc/download.sh

# Validate
uv run bids-hub arc validate data/openneuro/ds004884

# Upload
uv run bids-hub arc build data/openneuro/ds004884 --no-dry-run
\`\`\`

### ISLES24 Dataset
\`\`\`bash
# Download
./scripts/isles24/download.sh

# Validate
uv run bids-hub isles24 validate data/zenodo/isles24/train

# Upload
uv run bids-hub isles24 build data/zenodo/isles24/train --no-dry-run
\`\`\`
```

### Step 4: Update CLI Reference

**`docs/reference/cli.md`** - Add ISLES24 commands

### Step 5: Update Schema Reference

**`docs/reference/schema.md`** - Add ISLES24 schema

### Step 6: Create ISLES24 Tutorial

**`docs/tutorials/upload-isles24.md`**

### Step 7: Rename ARC Tutorial

```bash
mv docs/tutorials/first-upload.md docs/tutorials/upload-arc.md
```

---

## Success Criteria

- [ ] Dataset cards exist and are complete
- [ ] Index reflects multi-dataset support
- [ ] CLI reference updated
- [ ] Schema reference updated
- [ ] Tutorials for both datasets
- [ ] No broken internal links
- [ ] No stale ARC-only language

---

## Next Phase

After docs cleanup → Phase 06: Root Files Update
