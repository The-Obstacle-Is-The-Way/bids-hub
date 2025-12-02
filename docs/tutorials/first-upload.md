# Tutorial: Your First NIfTI Dataset Upload

> **Time**: 30 minutes (excluding upload time)
> **Prerequisites**: Python 3.10+, HuggingFace account, BIDS dataset on disk

This tutorial walks you through uploading a BIDS neuroimaging dataset to HuggingFace Hub using the `Nifti()` feature type.

---

## What You'll Learn

By the end of this tutorial, you will have:
1. Installed the required dependencies (with critical version pinning)
2. Built a file table from your BIDS dataset
3. Uploaded NIfTI files to HuggingFace Hub
4. Verified the upload works

---

## Step 1: Install Dependencies

**Critical**: You must install `datasets` from GitHub, not PyPI. The stable release has a bug that uploads empty files.

```bash
# Create a new project
mkdir my-bids-upload && cd my-bids-upload

# Initialize with uv (recommended)
uv init
uv add nibabel pandas huggingface-hub

# CRITICAL: Install datasets from git
uv add "datasets @ git+https://github.com/huggingface/datasets.git"
```

Verify the installation:

```python
import datasets
print(datasets.__version__)  # Should show "4.4.2.dev0" or similar
```

If you see `4.x.x` without `dev`, you have the wrong version.

---

## Step 2: Authenticate with HuggingFace

```bash
huggingface-cli login
```

Enter your token when prompted. You need write access to your target repository.

---

## Step 3: Explore Your BIDS Dataset

Your BIDS dataset should look like:

```
my-bids-dataset/
├── participants.tsv
├── dataset_description.json
├── sub-001/
│   └── ses-1/
│       ├── anat/
│       │   └── sub-001_ses-1_T1w.nii.gz
│       └── func/
│           └── sub-001_ses-1_bold.nii.gz
├── sub-002/
│   └── ...
```

---

## Step 4: Build a File Table

Create a Python script `build_dataset.py`:

```python
from pathlib import Path
import pandas as pd
from datasets import Dataset, Features, Value, Nifti

# Point to your BIDS root
bids_root = Path("my-bids-dataset")

# Build file table - one row per session
rows = []
for subject_dir in sorted(bids_root.glob("sub-*")):
    for session_dir in subject_dir.glob("ses-*"):
        # Find NIfTI files
        t1w_files = list((session_dir / "anat").glob("*_T1w.nii.gz"))
        bold_files = list((session_dir / "func").glob("*_bold.nii.gz"))

        rows.append({
            "subject_id": subject_dir.name,
            "session_id": session_dir.name,
            "t1w": str(t1w_files[0].resolve()) if t1w_files else None,
            "bold": str(bold_files[0].resolve()) if bold_files else None,
        })

file_table = pd.DataFrame(rows)
print(f"Built file table with {len(file_table)} rows")
print(file_table.head())
```

**Important**: File paths must be **absolute paths** as strings.

---

## Step 5: Define the Schema

```python
features = Features({
    "subject_id": Value("string"),
    "session_id": Value("string"),
    "t1w": Nifti(),      # Will hold actual NIfTI bytes
    "bold": Nifti(),     # Can be None if not present
})
```

---

## Step 6: Create and Upload the Dataset

```python
# Create dataset
ds = Dataset.from_pandas(file_table, preserve_index=False)
ds = ds.cast(features)

# Verify it works locally
print(ds[0])  # Should show NIfTI wrapper objects

# Upload to Hub
# CRITICAL: Set num_shards for datasets > 10GB
ds.push_to_hub(
    "your-username/your-dataset-name",
    embed_external_files=True,
    num_shards=len(file_table),  # One shard per row - prevents OOM
)
```

---

## Step 7: Verify the Upload

```python
from datasets import load_dataset

# Load from Hub
ds = load_dataset("your-username/your-dataset-name")

# Access a NIfTI file
nifti_image = ds["train"][0]["t1w"]
print(f"Shape: {nifti_image.shape}")
print(f"Affine: {nifti_image.affine}")
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Files are 0 bytes | Use `datasets` from git, not PyPI |
| OOM crash at 0% | Add `num_shards=len(file_table)` |
| Upload hangs | Run in `tmux`, check network |
| "Column not found" | Ensure all feature columns exist in DataFrame |

See [How-to Guides](../how-to/) for detailed solutions.

---

## Next Steps

- [Fix OOM Crashes](../how-to/fix-oom-crashes.md) - If uploading large datasets
- [Validate Before Upload](../how-to/validate-before-upload.md) - Ensure data integrity
- [Why Uploads Fail](../explanation/why-uploads-fail.md) - Understand the pitfalls
