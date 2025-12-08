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

```python
from datasets import load_dataset

ds = load_dataset("hugging-science/isles24-stroke", split="train")

# Access a subject
example = ds[0]
print(example["subject_id"])    # "sub-stroke0001"
print(example["ncct"])          # CT array
print(example["lesion_mask"])   # Segmentation mask
print(example["nihss_admission"])  # Stroke severity
```

## Citation

```bibtex
@article{isles2024,
  title={ISLES 2024: Ischemic Stroke Lesion Segmentation Challenge},
  author={ISLES Organizers},
  year={2024}
}
```
