# BIDS → HuggingFace Architecture Specification

> Date: 2025-12-07
> Status: **DRAFT** - Deep dive analysis for modular refactor
> Context: Clarifying what HuggingFace would want vs dataset-specific scripts

---

## Executive Summary

**The Key Insight:** This codebase already has the correct architecture pattern. The confusion
is namespace/organization, not fundamental design.

What we have:
```
GENERIC (what HF would integrate)     DATASET-SPECIFIC (per-upload scripts)
─────────────────────────────────     ─────────────────────────────────────
core.py                               arc.py
  - DatasetBuilderConfig              isles24.py
  - build_hf_dataset()                validation.py (ARC-only currently)
  - push_dataset_to_hub()             scripts/download_arc.sh
```

**The answer to your question:** Yes, HuggingFace would want `core.py` (the generic parts).
Individual researchers would then write dataset-specific modules like `arc.py`/`isles24.py`.

---

## What HuggingFace Would Want (Core Library)

### 1. Generic BIDS Utilities

These are **already generic** in our `core.py`:

```python
# DatasetBuilderConfig - Works for any BIDS dataset
@dataclass
class DatasetBuilderConfig:
    bids_root: Path
    hf_repo_id: str
    split: str | None = None
    dry_run: bool = False

# build_hf_dataset - Works for any file table + features
def build_hf_dataset(
    config: DatasetBuilderConfig,
    file_table: pd.DataFrame,  # ← Dataset provides this
    features: Features,         # ← Dataset provides this
) -> Dataset: ...

# push_dataset_to_hub - Works for any Dataset
def push_dataset_to_hub(
    ds: Dataset,
    config: DatasetBuilderConfig,
    embed_external_files: bool = True,
    **push_kwargs: Any,  # num_shards, etc.
) -> None: ...
```

### 2. What Would Be Added to Core (Not Yet Implemented)

```python
# Generic validation framework
class ValidationCheck:
    name: str
    expected: str
    actual: str
    passed: bool
    details: str = ""

class ValidationResult:
    bids_root: Path
    checks: list[ValidationCheck]

    @property
    def all_passed(self) -> bool: ...
    def summary(self) -> str: ...

# Generic BIDS file discovery helpers
def find_single_nifti(search_dir: Path, pattern: str) -> str | None: ...
def find_all_niftis(search_dir: Path, pattern: str) -> list[str]: ...

# Generic NIfTI integrity check
def check_nifti_integrity(bids_root: Path, sample_size: int = 10) -> ValidationCheck: ...

# Optional BIDS validator wrapper
def run_bids_validator(bids_root: Path) -> ValidationCheck | None: ...
```

### 3. What HuggingFace Would NOT Have

HuggingFace cannot provide:
- **Dataset-specific schemas** (ARC has WAB scores, ISLES24 has NIHSS)
- **Dataset-specific file patterns** (ARC uses `*_desc-lesion_mask.nii.gz`, ISLES24 uses `*_msk.nii.gz`)
- **Dataset-specific expected counts** (ARC expects 230 subjects, ISLES24 expects 149)
- **Dataset-specific download scripts** (OpenNeuro vs Zenodo)

**This is fundamental.** BIDS is a standard, but datasets diverge in:
1. What modalities they have
2. What metadata columns exist
3. How files are named (BIDS-ish vs strict BIDS)
4. Where derivatives live
5. What validation rules apply

---

## What Dataset-Specific Modules Do

Each dataset needs its own module that implements:

### Interface Contract (Implicit)

```python
# Every dataset module should implement:

def build_{dataset}_file_table(bids_root: Path) -> pd.DataFrame:
    """Walk BIDS directory, return DataFrame with one row per unit (subject/session)."""
    ...

def get_{dataset}_features() -> Features:
    """Return HuggingFace Features schema for this dataset."""
    ...

def build_and_push_{dataset}(config: DatasetBuilderConfig) -> None:
    """High-level orchestration: build file table → HF Dataset → push."""
    ...

# Optionally:
def validate_{dataset}_download(bids_root: Path, ...) -> ValidationResult:
    """Validate downloaded data before upload."""
    ...
```

### ARC Example (arc.py)

```python
# ARC-specific schema
Features({
    "subject_id": Value("string"),
    "session_id": Value("string"),
    "t1w": Nifti(),
    "t2w": Nifti(),
    "flair": Nifti(),
    "bold": Sequence(Nifti()),  # Multiple runs per session
    "dwi": Sequence(Nifti()),
    "sbref": Sequence(Nifti()),
    "lesion": Nifti(),
    "age_at_stroke": Value("float32"),
    "sex": Value("string"),
    "wab_aq": Value("float32"),
    "wab_type": Value("string"),
})
```

### ISLES24 Example (isles24.py)

```python
# ISLES24-specific schema (completely different!)
Features({
    "subject_id": Value("string"),
    "ncct": Nifti(),
    "cta": Nifti(),
    "ctp": Nifti(),
    "tmax": Nifti(),
    "mtt": Nifti(),
    "cbf": Nifti(),
    "cbv": Nifti(),
    "dwi": Nifti(),
    "adc": Nifti(),
    "lesion_mask": Nifti(),
    "lvo_mask": Nifti(),
    "cow_segmentation": Nifti(),
    "age": Value("float32"),
    "sex": Value("string"),
    "nihss_admission": Value("float32"),
    "mrs_3month": Value("float32"),
    "thrombolysis": Value("string"),
    "thrombectomy": Value("string"),
})
```

---

## Current State Analysis

### What's Correct ✅

| Component | Location | Status |
|-----------|----------|--------|
| `DatasetBuilderConfig` | `core.py` | Generic ✅ |
| `build_hf_dataset()` | `core.py` | Generic ✅ |
| `push_dataset_to_hub()` | `core.py` | Generic ✅ |
| `build_arc_file_table()` | `arc.py` | Dataset-specific ✅ |
| `build_isles24_file_table()` | `isles24.py` | Dataset-specific ✅ |
| `get_arc_features()` | `arc.py` | Dataset-specific ✅ |
| `get_isles24_features()` | `isles24.py` | Dataset-specific ✅ |

### What's Misplaced ❌

| Component | Location | Problem | Fix |
|-----------|----------|---------|-----|
| `ValidationCheck` | `validation.py` | Should be generic | Move to `validation/base.py` |
| `ValidationResult` | `validation.py` | Should be generic | Move to `validation/base.py` |
| `EXPECTED_COUNTS` | `validation.py` | ARC-specific | Move to `validation/arc.py` |
| `validate_arc_download()` | `validation.py` | Correctly named, wrong location | Move to `validation/arc.py` |
| Package name | `pyproject.toml` | `arc-bids` is misleading | Future: rename to `bids-hf` |

### What's Missing ❌

| Component | Needed For |
|-----------|------------|
| `validation/base.py` | Generic validation classes |
| `validation/isles24.py` | ISLES24 validation |
| `scripts/download_isles24.sh` | Download from Zenodo |
| `scripts/validate_hf_isles24.py` | Round-trip validation |
| Dataset cards | HF README files |

---

## Proposed Package Structure

```
src/
├── bids_hf/                        # Rename from arc_bids (future)
│   ├── __init__.py
│   │
│   ├── core/                       # GENERIC (what HF would want)
│   │   ├── __init__.py
│   │   ├── builder.py              # build_hf_dataset, push_dataset_to_hub
│   │   ├── config.py               # DatasetBuilderConfig
│   │   └── utils.py                # find_single_nifti, find_all_niftis
│   │
│   ├── validation/                 # GENERIC + DATASET-SPECIFIC
│   │   ├── __init__.py
│   │   ├── base.py                 # ValidationCheck, ValidationResult (generic)
│   │   ├── arc.py                  # EXPECTED_COUNTS, validate_arc_download
│   │   └── isles24.py              # ISLES24_EXPECTED, validate_isles24_download
│   │
│   ├── datasets/                   # DATASET-SPECIFIC
│   │   ├── __init__.py
│   │   ├── arc.py                  # build_arc_file_table, get_arc_features
│   │   └── isles24.py              # build_isles24_file_table, get_isles24_features
│   │
│   └── cli.py                      # CLI with arc/isles24 subcommands

scripts/                            # DATASET-SPECIFIC
├── arc/
│   ├── download.sh
│   ├── validate_download.py
│   └── validate_hf_upload.py
└── isles24/
    ├── download.sh
    ├── validate_download.py
    └── validate_hf_upload.py

docs/
├── dataset-cards/
│   ├── arc-aphasia-bids.md         # HF README for ARC
│   └── isles24-stroke.md           # HF README for ISLES24
└── ...
```

---

## Phased Implementation Plan

### Phase 0: Upload ISLES24 First (IMMEDIATE)

**Goal:** Get ISLES24 on HuggingFace using current architecture.

No refactoring needed. Use what we have:
- `isles24.py` is already implemented
- Download is in progress
- Just validate structure and upload

### Phase 1: Extract Generic Validation (SMALL REFACTOR)

**Goal:** Make `ValidationCheck` and `ValidationResult` reusable.

```bash
# Create validation subpackage
mkdir -p src/arc_bids/validation
touch src/arc_bids/validation/__init__.py

# Move generic classes
# base.py: ValidationCheck, ValidationResult, _check_nifti_integrity
# arc.py: EXPECTED_COUNTS, validate_arc_download, _check_* helpers
# isles24.py: ISLES24_EXPECTED, validate_isles24_download (NEW)
```

Tests:
```python
# test_validation_base.py
def test_validation_check_creation(): ...
def test_validation_result_all_passed(): ...
def test_validation_result_summary(): ...

# test_validation_arc.py
def test_validate_arc_download(): ...  # Move existing tests

# test_validation_isles24.py
def test_validate_isles24_download(): ...  # NEW
```

### Phase 2: Organize Scripts by Dataset

**Goal:** Clear namespace for per-dataset scripts.

```bash
# Current (confusing)
scripts/
├── download_arc.sh
├── validate_download.py        # ARC only, not obvious
└── validate_hf_download.py     # ARC only, not obvious

# After (clear)
scripts/
├── arc/
│   ├── download.sh
│   ├── validate_download.py
│   └── validate_hf_upload.py
└── isles24/
    ├── download.sh
    ├── validate_download.py
    └── validate_hf_upload.py
```

### Phase 3: Add ISLES24 Validation (NEW FEATURE)

**Goal:** Validate ISLES24 downloads before upload.

```python
# src/arc_bids/validation/isles24.py

ISLES24_EXPECTED_COUNTS = {
    "subjects": 149,
    "ncct": 149,
    "cta": 149,
    "ctp": 140,      # Some missing
    "dwi": 149,
    "adc": 149,
    "lesion_mask": 149,
    "tmax": 140,
    "mtt": 140,
    "cbf": 140,
    "cbv": 140,
    "lvo_mask": 100,  # Optional
    "cow_segmentation": 100,  # Optional
}

def validate_isles24_download(
    bids_root: Path,
    nifti_sample_size: int = 10,
    tolerance: float = 0.1,  # 10% for optional modalities
) -> ValidationResult: ...
```

### Phase 4: Package Rename (FUTURE - 3+ datasets)

**Goal:** Generic package name when we have enough datasets.

```toml
# pyproject.toml
[project]
name = "bids-hf"  # or "bids-to-hf" or "bids-datasets"
```

**Deferred until:** We have 3+ datasets (ARC, ISLES24, ATLAS, etc.)

---

## TDD Test Structure

```python
# tests/
├── conftest.py                 # Shared fixtures
├── core/
│   ├── test_builder.py         # build_hf_dataset tests
│   ├── test_config.py          # DatasetBuilderConfig tests
│   └── test_utils.py           # File discovery tests
├── validation/
│   ├── test_base.py            # Generic validation tests
│   ├── test_arc.py             # ARC validation tests
│   └── test_isles24.py         # ISLES24 validation tests
├── datasets/
│   ├── test_arc.py             # ARC file table/features tests
│   └── test_isles24.py         # ISLES24 file table/features tests
└── test_cli.py                 # CLI integration tests
```

### Key Test Patterns

1. **Synthetic BIDS fixtures** - Create minimal valid structures
2. **Mock push_to_hub** - Don't actually upload during tests
3. **Expected counts** - Validate against paper/source counts
4. **NIfTI integrity** - Create minimal 2x2x2 NIfTI files

---

## FAQ

### Q: Why can't HuggingFace just have a universal BIDS loader?

BIDS defines directory structure, not schema. Two BIDS datasets can have:
- Different modalities (ARC has WAB scores, ISLES24 has NIHSS)
- Different session structures (ARC is longitudinal, ISLES24 is flattened)
- Different derivatives (lesion masks vs perfusion maps)
- Different naming conventions (strict BIDS vs BIDS-ish)

A "universal BIDS loader" would need to:
1. Auto-detect all modalities present
2. Infer schema from directory structure
3. Handle arbitrary derivatives
4. Deal with non-standard naming

This is **exactly what bids-validator does** - and it's 50K+ lines of code.

### Q: So what IS generic?

1. **File embedding** - Reading NIfTI bytes into Parquet
2. **Sharding** - Splitting large datasets
3. **Upload mechanics** - HfApi, chunked uploads
4. **Validation framework** - ValidationCheck/ValidationResult pattern
5. **File discovery helpers** - find_single_nifti, find_all_niftis

### Q: What's always dataset-specific?

1. **Schema** - What columns exist, what types
2. **File patterns** - Where each modality lives
3. **Expected counts** - How many files should exist
4. **Metadata mapping** - participants.tsv column names
5. **Download source** - OpenNeuro vs Zenodo vs Grand Challenge

---

## Bottom Line

**The architecture is correct.** The confusion is namespace/organization.

1. `core.py` = What HuggingFace would ship
2. `arc.py` / `isles24.py` = What researchers write per-dataset
3. Scripts need reorganization by dataset namespace

**Immediate priority:** Upload ISLES24 with current code, then refactor.

---

## Related Documents

- `modular-refactor-spec.md` - Previous partial spec
- `isles24-full-upload-spec.md` - ISLES24 upload details
- `isles24-upload-brainstorm.md` - Original brainstorm
