# CLI Reference

> Command-line interface for bids-hub.

---

## Installation

```bash
uv add bids-hub
# or
pip install bids-hub
```

---

## Global Commands

### `bids-hub --help`

Show the help message and available subcommands.

### `bids-hub list`

List all supported datasets.

```bash
bids-hub list
```

**Output:**
```text
Supported datasets:
  arc     - Aphasia Recovery Cohort (OpenNeuro ds004884)
  isles24 - ISLES 2024 Stroke (Zenodo)
```

---

## ARC Commands

### `bids-hub arc build`

Build and upload the ARC dataset to HuggingFace Hub.

```bash
bids-hub arc build <bids_root> [options]
```

**Arguments:**
- `bids_root`: Path to the ARC BIDS dataset root (ds004884).

**Options:**
- `--hf-repo`, `-r`: HuggingFace repo ID. Default: `hugging-science/arc-aphasia-bids`
- `--dry-run`: Build dataset locally without pushing to Hub. Default: `True`
- `--no-dry-run`: Explicitly disable dry run (push to Hub).

**Example:**
```bash
bids-hub arc build data/openneuro/ds004884 --no-dry-run
```

### `bids-hub arc validate`

Validate an ARC dataset download.

```bash
bids-hub arc validate <bids_root> [options]
```

**Options:**
- `--bids-validator/--no-bids-validator`: Run external BIDS validator. Default: `False`
- `--sample-size`, `-n`: Number of NIfTI files to spot-check. Default: `10`
- `--tolerance`, `-t`: Allowed fraction of missing files. Default: `0.0`

### `bids-hub arc info`

Show information about the ARC dataset (size, modalities, source).

---

## ISLES24 Commands

### `bids-hub isles24 build`

Build and upload the ISLES24 dataset to HuggingFace Hub.

```bash
bids-hub isles24 build <bids_root> [options]
```

**Arguments:**
- `bids_root`: Path to the ISLES'24 dataset root (train/).

**Options:**
- `--hf-repo`, `-r`: HuggingFace repo ID. Default: `hugging-science/isles24-stroke`
- `--dry-run`: Build dataset locally without pushing to Hub. Default: `True`
- `--no-dry-run`: Explicitly disable dry run (push to Hub).

**Example:**
```bash
bids-hub isles24 build data/zenodo/isles24/train --no-dry-run
```

### `bids-hub isles24 validate`

Validate an ISLES24 dataset download.

```bash
bids-hub isles24 validate <bids_root> [options]
```

**Options:**
- `--sample-size`, `-n`: Number of NIfTI files to spot-check. Default: `10`
- `--tolerance`, `-t`: Allowed fraction of missing files. Default: `0.1` (10%)

### `bids-hub isles24 info`

Show information about the ISLES'24 dataset.
