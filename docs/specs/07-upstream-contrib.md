# Phase 07: Upstream Contribution (Future)

> Status: FUTURE - After 3+ datasets working
> Blocking: No
> Estimated: Ongoing engagement with HuggingFace team

---

## Goal

Contribute core BIDS→HF infrastructure to the upstream `datasets` library.

---

## Why This Matters

**Current Pain (for researchers):**
- Must figure out `Nifti()` embedding from scratch
- Must discover sharding strategies through trial and error
- Must work around bugs (#7893, #7894) themselves
- 500+ lines of code for something that should be simple

**After Upstream Integration:**
```python
# Dream API
from datasets import BidsDataset

ds = BidsDataset.from_bids(
    bids_root="data/my-dataset",
    schema={
        "t1w": "anat/*_T1w.nii.gz",
        "lesion": "derivatives/masks/*_lesion.nii.gz",
    },
    metadata_from="participants.tsv",
)

ds.push_to_hub("my-org/my-dataset")
```

---

## What We Would Contribute

### 1. Core Builder Functions

```python
# Already in our core.py
def build_hf_dataset(
    file_table: pd.DataFrame,
    features: Features,
) -> Dataset: ...

def push_dataset_to_hub(
    ds: Dataset,
    repo_id: str,
    num_shards: int | None = None,
    embed_external_files: bool = True,
) -> None: ...
```

### 2. Validation Framework

```python
# Generic validation classes
@dataclass
class ValidationCheck:
    name: str
    expected: str
    actual: str
    passed: bool

@dataclass
class ValidationResult:
    checks: list[ValidationCheck]

    @property
    def all_passed(self) -> bool: ...
    def summary(self) -> str: ...
```

### 3. File Discovery Utilities

```python
def find_nifti(path: Path, pattern: str) -> str | None: ...
def find_all_niftis(path: Path, pattern: str) -> list[str]: ...
```

### 4. Bug Fixes / Workarounds

- #7893: `Nifti.embed_storage` empty file bug
- #7894: `embed_table_storage` SIGKILL on sharded Sequence(Nifti())

---

## What Would NOT Be Upstream

Dataset-specific code stays in user repos:
- Schema definitions
- File pattern mappings
- Expected counts for validation
- Download scripts
- Dataset cards

---

## Contribution Strategy

### Phase 1: Prove It Works (Current)

- Upload ARC (done)
- Upload ISLES24 (in progress)
- Upload 1-2 more datasets (ATLAS, etc.)
- Document patterns that emerge

### Phase 2: Extract Clean Core

- Remove all dataset-specific code from core
- Write comprehensive tests
- Document API thoroughly
- Create standalone package or PR-ready branch

### Phase 3: Engage HuggingFace

- Open discussion on `datasets` GitHub
- Reference working datasets as proof of concept
- Propose API design
- Iterate on feedback

### Phase 4: Contribute

- PR to `datasets` library
- Or: Publish as `bids-datasets` package on PyPI
- Maintain compatibility with upstream `datasets`

---

## Realistic Timeline

| Milestone | Estimate |
|-----------|----------|
| ISLES24 uploaded | This week |
| 3rd dataset (ATLAS?) | 2-4 weeks |
| Clean core extraction | 1-2 weeks |
| HF discussion opened | After 3 datasets |
| Actual contribution | TBD (depends on HF response) |

---

## Alternative: Standalone Package

If HuggingFace is slow to respond, we could:

1. Rename this repo to `bids-hf` or `bids-datasets`
2. Publish to PyPI
3. Market to neuroimaging community
4. Let organic adoption drive upstream interest

```bash
pip install bids-hf

# Usage
from bids_hf import build_hf_dataset, push_dataset_to_hub
```

---

## Related

- HuggingFace datasets repo: https://github.com/huggingface/datasets
- `Nifti()` feature type: Added in datasets 3.x
- Discord discussions: HF Discord #medical-imaging channel

---

## Notes

This phase is deliberately vague because it depends on:
1. How many datasets we successfully upload
2. What patterns emerge from diverse datasets
3. HuggingFace team's receptiveness
4. Community interest

Focus on Phases 01-06 first. This is the long-term vision.
