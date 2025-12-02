# arc-aphasia-bids

Upload the **Aphasia Recovery Cohort (ARC)** dataset to Hugging Face Hub.

> **Status**: Phase 0 (Setup & Exploration)
> **Target HF Repo**: `the-obstacle-is-the-way/arc-aphasia-bids`

## What is ARC?

The [Aphasia Recovery Cohort (ARC)](https://openneuro.org/datasets/ds004884) is a BIDS-formatted neuroimaging dataset containing:

- **230 chronic stroke patients** with aphasia
- **902 scanning sessions** (longitudinal)
- **Imaging**: T1w, T2w, FLAIR, diffusion, fMRI, resting-state (NIfTI)
- **Annotations**: Expert-drawn lesion maps
- **Tabular**: Demographics + WAB (Western Aphasia Battery) scores

**Source**: [OpenNeuro ds004884](https://openneuro.org/datasets/ds004884/versions/1.0.1)
**Paper**: [Scientific Data (2024)](https://www.nature.com/articles/s41597-024-03819-7)
**License**: CC0 (Public Domain) - Redistribution OK

## Goal

Convert ARC from BIDS → HuggingFace Dataset that:
1. Works with `datasets.load_dataset()`
2. Uses HF's `Nifti()` feature type for lazy NIfTI loading
3. Enables `push_to_hub()` workflow
4. Renders in HF Hub viewer via NiiVue integration

## Architecture

This repo was created from the [hf-bids-nifti-datasets](https://github.com/The-Obstacle-Is-The-Way/hf-bids-nifti-datasets) template.

### Data Flow

```
OpenNeuro ds004884 (BIDS)
        │
        ▼ AWS S3 or OpenNeuro CLI
Local: data/openneuro/ds004884/  (gitignored)
        │
        ▼ Python walks BIDS tree
pandas DataFrame (paths + metadata)
        │
        ▼ build_hf_dataset()
datasets.Dataset with Nifti() features
        │
        ▼ push_to_hub()
HF Hub (via XET storage)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `src/hf_bids_nifti/core.py` | Generic BIDS→HF Dataset conversion |
| `src/hf_bids_nifti/arc.py` | ARC-specific builder (to implement) |
| `src/hf_bids_nifti/cli.py` | Typer CLI |
| `scripts/download_arc.sh` | Download ARC from OpenNeuro |

## Quickstart

```bash
# Clone
git clone https://github.com/The-Obstacle-Is-The-Way/arc-aphasia-bids.git
cd arc-aphasia-bids

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Download ARC dataset (choose S3 or subset)
./scripts/download_arc.sh

# Once implemented:
uv run hf-bids-nifti arc data/openneuro/ds004884 \
  --hf-repo the-obstacle-is-the-way/arc-aphasia-bids \
  --dry-run
```

## Downloading ARC

### Option 1: AWS S3 (Recommended - No Auth)

```bash
aws s3 sync --no-sign-request s3://openneuro.org/ds004884 data/openneuro/ds004884
```

### Option 2: Interactive Script

```bash
./scripts/download_arc.sh
# Choose: 1) Full dataset, 2) Subset for testing, 3) OpenNeuro CLI
```

### Option 3: OpenNeuro CLI (Deno)

```bash
# Install Deno + CLI
curl -fsSL https://deno.land/install.sh | sh
deno install -A --global jsr:@openneuro/cli -n openneuro
openneuro login  # requires API key

# Download
openneuro download ds004884 data/openneuro/ds004884
```

## Project Structure

```
arc-aphasia-bids/
├── src/hf_bids_nifti/
│   ├── core.py          # Generic BIDS→HF logic
│   ├── arc.py           # ARC builder (STUB - to implement)
│   └── cli.py           # CLI
├── scripts/
│   └── download_arc.sh  # Download script
├── tests/               # pytest tests
├── data/                # (gitignored) Local data
│   └── openneuro/ds004884/
├── docs/                # Documentation
└── pyproject.toml
```

## Overview

This repository provides a **reusable template** for:

```
BIDS dataset on disk → Pandas table of NIfTI file paths + metadata → HF Dataset with Nifti features → optional push_to_hub()
```

**Key points:**

- **No real data in this repo** - Only code and scaffolding
- Data will be mirrored from OpenNeuro directly to Hugging Face datasets
- Respects CC0 licensing from source datasets
- Designed for TDD with fake-data tests

### Target Datasets

| Dataset | OpenNeuro ID | Description |
|---------|--------------|-------------|
| ARC | [ds004884](https://openneuro.org/datasets/ds004884) | Aphasia Recovery Cohort - structural MRI & lesion masks |
| SOOP | [ds004889](https://openneuro.org/datasets/ds004889) | Study of Outcomes in aPhagia - longitudinal stroke recovery |

## Quickstart

```bash
# Clone
git clone https://github.com/The-Obstacle-Is-The-Way/hf-bids-nifti-datasets.git
cd hf-bids-nifti-datasets

# Install dependencies (requires uv: https://docs.astral.sh/uv/)
uv sync

# Run tests
uv run pytest

# See CLI help
uv run hf-bids-nifti --help
```

> **Note:** ARC and SOOP commands are templates that will raise `NotImplementedError` until their file-table builders are implemented.

## Project Structure

```
hf-bids-nifti-datasets/
├── src/
│   └── hf_bids_nifti/
│       ├── __init__.py      # Package exports
│       ├── core.py          # Generic BIDS→HF Dataset logic
│       ├── config.py        # Dataset configuration objects
│       ├── arc.py           # ARC-specific STUB
│       ├── soop.py          # SOOP-specific STUB
│       └── cli.py           # Typer CLI
├── tests/
│   ├── test_core_nifti.py   # Core functionality tests
│   └── test_cli_skeleton.py # CLI tests
├── pyproject.toml           # PEP 621 project config
├── uv.lock                  # Reproducible dependencies
├── Makefile                 # Dev workflow automation
├── .pre-commit-config.yaml  # Pre-commit hooks
├── mypy.ini                 # Type checking config
└── README.md
```

## Usage

### As a Library

```python
from pathlib import Path
import pandas as pd
from datasets import Features, Nifti, Value

from hf_bids_nifti.core import DatasetBuilderConfig, build_hf_dataset

# Create a file table with paths to NIfTI files
file_table = pd.DataFrame({
    "subject_id": ["sub-001", "sub-002"],
    "t1w": ["/path/to/sub-001_T1w.nii.gz", "/path/to/sub-002_T1w.nii.gz"],
    "age": [25.0, 30.0],
})

# Define the HF Features schema
features = Features({
    "subject_id": Value("string"),
    "t1w": Nifti(),
    "age": Value("float32"),
})

# Build the dataset
config = DatasetBuilderConfig(
    bids_root=Path("/path/to/bids"),
    hf_repo_id="your-username/your-dataset",
    dry_run=True,
)
ds = build_hf_dataset(config, file_table, features)

# Access NIfTI data
img = ds[0]["t1w"]  # Returns nibabel.Nifti1Image
data = img.get_fdata()  # Convert to numpy array
```

### CLI (Templates)

```bash
# ARC dataset (template - will raise NotImplementedError)
uv run hf-bids-nifti arc /path/to/ds004884 --hf-repo user/arc-demo --dry-run

# SOOP dataset (template - will raise NotImplementedError)
uv run hf-bids-nifti soop /path/to/ds004889 --hf-repo user/soop-demo --dry-run
```

## Development

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management

### Setup

```bash
# Install all dependencies (including dev)
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Common Commands

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Lint code
make lint

# Format code
make format

# Type check
make typecheck

# Run all pre-commit hooks
make pre-commit
```

### Adding a New Dataset

1. Create a new module (e.g., `src/hf_bids_nifti/mydataset.py`)
2. Implement `build_mydataset_file_table(bids_root: Path) -> pd.DataFrame`
3. Define `get_mydataset_features() -> Features`
4. Create `build_and_push_mydataset(config: DatasetBuilderConfig)`
5. Add CLI command in `cli.py`
6. Add tests in `tests/test_mydataset.py`

## Architecture

### Core Concepts

- **`DatasetBuilderConfig`**: Configuration dataclass holding BIDS root path, HF repo ID, and options
- **`build_hf_dataset()`**: Generic function that converts a pandas DataFrame with NIfTI paths to an HF Dataset
- **`Features` with `Nifti()`**: HF schema that enables automatic NIfTI loading via nibabel

### Workflow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  BIDS Directory │────▶│  File Table (df) │────▶│  HF Dataset     │
│  (on disk)      │     │  paths + metadata│     │  Nifti + Values │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        │                        │                        │
   walk directory         pandas DataFrame          ds.push_to_hub()
   extract metadata       with NIfTI paths          to HF Hub
```

## References

- [HuggingFace Datasets - NIfTI](https://huggingface.co/docs/datasets/en/nifti_dataset)
- [BIDS Specification](https://bids-specification.readthedocs.io/)
- [OpenNeuro](https://openneuro.org/)
- [nibabel Documentation](https://nipy.org/nibabel/)

## License

Apache-2.0

The source datasets (ARC, SOOP) are released under CC0 (Public Domain) on OpenNeuro.
