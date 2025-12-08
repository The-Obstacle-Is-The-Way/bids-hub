# Phase 02: Validation Module Refactor

> Status: Ready after Phase 01
> Blocking: No
> Estimated: 2-3 hours

---

## Goal

Split `validation.py` into:
- `validation/base.py` - Generic classes (upstream candidate)
- `validation/arc.py` - ARC-specific validation
- `validation/isles24.py` - ISLES24-specific validation (NEW)

---

## Current State

```python
# src/arc_bids/validation.py (387 lines)

# GENERIC (should be reusable)
@dataclass
class ValidationCheck: ...
@dataclass
class ValidationResult: ...
def _check_nifti_integrity(): ...
def _check_bids_validator(): ...

# ARC-SPECIFIC (should move)
EXPECTED_COUNTS = {...}  # ARC paper counts
REQUIRED_BIDS_FILES = [...]  # ARC requirements
def _check_required_files(): ...
def _check_subject_count(): ...
def _check_series_count(): ...
def validate_arc_download(): ...
```

---

## Target State

```
src/arc_bids/validation/
├── __init__.py          # Re-exports for backward compat
├── base.py              # Generic validation framework
├── arc.py               # ARC-specific
└── isles24.py           # ISLES24-specific (NEW)
```

---

## Implementation Steps

### Step 1: Create Directory Structure

```bash
mkdir -p src/arc_bids/validation
touch src/arc_bids/validation/__init__.py
```

### Step 2: Create `base.py`

```python
# src/arc_bids/validation/base.py
"""Generic validation framework for BIDS datasets."""

from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ValidationCheck:
    """Result of a single validation check."""
    name: str
    expected: str
    actual: str
    passed: bool
    details: str = ""

@dataclass
class ValidationResult:
    """Complete validation results for a BIDS download."""
    bids_root: Path
    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool: ...

    @property
    def passed_count(self) -> int: ...

    @property
    def failed_count(self) -> int: ...

    def add(self, check: ValidationCheck) -> None: ...

    def summary(self) -> str: ...

# Generic helpers
def check_nifti_integrity(
    bids_root: Path,
    pattern: str = "*_T1w.nii.gz",
    sample_size: int = 10,
) -> ValidationCheck: ...

def check_bids_validator(bids_root: Path) -> ValidationCheck | None: ...

def check_file_exists(path: Path, name: str) -> ValidationCheck: ...

def check_count(
    name: str,
    actual: int,
    expected: int,
    tolerance: float = 0.0,
) -> ValidationCheck: ...
```

### Step 3: Create `arc.py`

```python
# src/arc_bids/validation/arc.py
"""ARC dataset validation."""

from pathlib import Path
from .base import ValidationCheck, ValidationResult, check_nifti_integrity, check_bids_validator

# From Sci Data paper (Gibson et al., 2024)
EXPECTED_COUNTS = {
    "subjects": 230,
    "sessions": 902,
    "t1w_series": 441,
    "t2w_series": 447,
    "flair_series": 235,
    "bold_series": 850,
    "dwi_series": 613,
    "sbref_series": 88,
    "lesion_masks": 230,
}

REQUIRED_BIDS_FILES = [
    "dataset_description.json",
    "participants.tsv",
    "participants.json",
]

def validate_arc_download(
    bids_root: Path,
    run_bids_validator: bool = False,
    nifti_sample_size: int = 10,
    tolerance: float = 0.0,
) -> ValidationResult: ...
```

### Step 4: Create `isles24.py`

```python
# src/arc_bids/validation/isles24.py
"""ISLES24 dataset validation."""

from pathlib import Path
from .base import ValidationCheck, ValidationResult, check_nifti_integrity

# From Zenodo record / challenge description
EXPECTED_COUNTS = {
    "subjects": 149,
    "ncct": 149,
    "cta": 149,
    "ctp": 140,        # ~94% have CTP
    "dwi": 149,
    "adc": 149,
    "lesion_mask": 149,
    "tmax": 140,
    "mtt": 140,
    "cbf": 140,
    "cbv": 140,
    "lvo_mask": 100,   # Optional (~67%)
    "cow_segmentation": 100,  # Optional (~67%)
}

REQUIRED_FILES = [
    "clinical_data-description.xlsx",  # NOTE: NOT participants.tsv!
    # Note: ISLES24 uses xlsx metadata, not standard BIDS participants.tsv
]

def validate_isles24_download(
    bids_root: Path,
    nifti_sample_size: int = 10,
    tolerance: float = 0.1,  # 10% tolerance for optional modalities
) -> ValidationResult: ...
```

### Step 5: Update `__init__.py`

```python
# src/arc_bids/validation/__init__.py
"""Validation module - re-exports for backward compatibility."""

from .base import ValidationCheck, ValidationResult
from .arc import EXPECTED_COUNTS, validate_arc_download
from .isles24 import validate_isles24_download

__all__ = [
    "ValidationCheck",
    "ValidationResult",
    "EXPECTED_COUNTS",
    "validate_arc_download",
    "validate_isles24_download",
]
```

### Step 6: Update Imports

Files to update:
- `src/arc_bids/__init__.py`
- `src/arc_bids/cli.py`
- `scripts/validate_download.py`

### Step 7: Delete Old File

```bash
rm src/arc_bids/validation.py
```

---

## Tests

### Existing Tests (Move)

```bash
# Rename/move existing tests
mv tests/test_validation.py tests/validation/test_arc.py
```

### New Tests

```python
# tests/validation/test_base.py
def test_validation_check_creation(): ...
def test_validation_result_all_passed_true(): ...
def test_validation_result_all_passed_false(): ...
def test_validation_result_summary_format(): ...
def test_check_nifti_integrity_valid(): ...
def test_check_nifti_integrity_corrupt(): ...

# tests/validation/test_isles24.py
def test_validate_isles24_download_valid(synthetic_isles24_root): ...
def test_validate_isles24_download_missing_modality(): ...
def test_validate_isles24_tolerance(): ...
```

---

## CLI Update

Add `isles24 validate` subcommand:

```python
# src/arc_bids/cli.py

@isles_app.command("validate")
def validate_isles(
    bids_root: Path = typer.Argument(...),
    sample_size: int = typer.Option(10),
    tolerance: float = typer.Option(0.1),
) -> None:
    """Validate an ISLES24 dataset download."""
    from .validation.isles24 import validate_isles24_download

    result = validate_isles24_download(bids_root, sample_size, tolerance)
    typer.echo(result.summary())

    if not result.all_passed:
        raise typer.Exit(code=1)
```

---

## Success Criteria

- [ ] `from arc_bids.validation import validate_arc_download` still works
- [ ] `from arc_bids.validation import validate_isles24_download` works
- [ ] `arc-bids validate` still works (ARC)
- [ ] `arc-bids isles24 validate` works (NEW)
- [ ] All existing tests pass
- [ ] New ISLES24 validation tests pass
- [ ] mypy passes
- [ ] ruff passes

---

## Next Phase

After validation refactor → Phase 03: Scripts Reorganization
