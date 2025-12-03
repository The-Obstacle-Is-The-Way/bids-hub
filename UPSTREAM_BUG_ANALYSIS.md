# Upstream Bug Analysis: HuggingFace Datasets + Nifti Embedding

**Status**: TWO BUGS DISCOVERED - Both workarounds implemented
**Date**: 2025-12-02
**Severity**: P0 (Blocking)

---

## Summary

Two separate bugs in HuggingFace `datasets` library prevent uploading large neuroimaging datasets:

| Bug | Symptom | Root Cause | Fix |
|-----|---------|------------|-----|
| **Bug 1** | OOM crash, exit 137 | Memory accumulation in `additions` list | Custom one-shard-at-a-time uploader |
| **Bug 2** | SIGKILL in `embed_table_storage` | Internal Arrow references in sharded datasets | Pandas round-trip |

---

## Bug 1: Memory Accumulation in `_push_parquet_shards_to_hub`

### Symptom

Upload crashes at "Uploading Shards: X%" with exit code 137 (OOM killer).

### Root Cause

In `datasets/arrow_dataset.py`, the `_push_parquet_shards_to_hub` function keeps ALL shard bytes in memory:

```python
additions = []
for shard in shards:
    parquet_content = shard.to_parquet_bytes()  # ~300 MB
    shard_addition = CommitOperationAdd(path_or_fileobj=parquet_content)
    api.preupload_lfs_files(additions=[shard_addition])
    additions.append(shard_addition)  # THE BUG: keeps bytes alive
```

**Result**: 902 shards × 300 MB = ~270 GB RAM requested → OOM.

### Fix

Custom uploader that processes one shard at a time, writes to disk, uploads, then deletes:

```python
for i in range(num_shards):
    shard = ds.shard(num_shards=num_shards, index=i, contiguous=True)
    # Process, upload, delete - memory stays constant
```

---

## Bug 2: `embed_table_storage` Crashes on Sharded Datasets with `Sequence(Nifti())`

### Symptom

Even with Bug 1 fixed, upload crashes at "Uploading Shards: 0%" on the FIRST shard with:
- Exit code 137 (SIGKILL)
- "semaphore leak" warning (symptom, not cause)

### Root Cause

When `ds.shard()` or `ds.select()` creates a subset, the resulting Arrow table has internal references that cause `embed_table_storage` to crash when processing `Sequence(Nifti())` columns.

**Key evidence**:
- Manually created datasets work fine
- `ds.shard(...)` datasets crash
- `ds.select([i])` datasets crash (not just shard)
- Crash happens specifically on `Sequence(Nifti())` columns (bold, dwi, sbref)
- Crash happens even when the Sequence is an empty list

### Disproven Hypotheses

| Hypothesis | Test | Result |
|------------|------|--------|
| PyArrow 2GB binary limit | Monkey-patched `Nifti.pa_type` to use `pa.large_binary()` | STILL CRASHED |
| Memory mapping issue | Called `table.combine_chunks()` to force deep copy | STILL CRASHED |
| File size issue | Tested with small NIfTI files | STILL CRASHED |

### Fix

Convert shard to pandas and recreate the Dataset to break problematic internal references:

```python
shard = ds.shard(num_shards=num_shards, index=i, contiguous=True)

# CRITICAL FIX: Convert to pandas and back
shard_df = shard.to_pandas()
fresh_shard = Dataset.from_pandas(shard_df, preserve_index=False)
fresh_shard = fresh_shard.cast(ds.features)

# Now embedding works
table = fresh_shard._data.table.combine_chunks()
embedded_table = embed_table_storage(table)
```

---

## Minimal Reproduction (for upstream bug report)

```python
from datasets import Dataset, Features, Sequence
from datasets.features import Nifti
from datasets.table import embed_table_storage

# Create dataset with Sequence(Nifti())
features = Features({
    "id": Value("string"),
    "images": Sequence(Nifti()),
})

ds = Dataset.from_dict({
    "id": ["a", "b"],
    "images": [
        ["/path/to/file1.nii.gz", "/path/to/file2.nii.gz"],
        [],
    ],
}).cast(features)

# This works
table = ds._data.table.combine_chunks()
embedded = embed_table_storage(table)  # OK

# Create a shard
shard = ds.shard(num_shards=2, index=0, contiguous=True)

# This crashes with SIGKILL
shard_table = shard._data.table.combine_chunks()
embedded = embed_table_storage(shard_table)  # CRASH
```

---

## Environment

- macOS 14.x (ARM64)
- Python 3.13
- PyArrow 18.1.0
- datasets (git main, post-0.22.0)
- huggingface_hub 0.30.0

---

## Related Upstream Issues

### HuggingFace Datasets

| Issue | Title | Status | Relevance |
|-------|-------|--------|-----------|
| [#6360](https://github.com/huggingface/datasets/issues/6360) | Sequence(Audio/Image) not embedded in push_to_hub | Closed | Same code path |
| [#5672](https://github.com/huggingface/datasets/issues/5672) | Pushing dataset to hub crash | Open | Similar symptom |
| [#5990](https://github.com/huggingface/datasets/issues/5990) | Large dataset push hangs | Open | Related |

---

## References

- [datasets.table.embed_table_storage source](https://github.com/huggingface/datasets/blob/main/src/datasets/table.py)
- [datasets.features.nifti source](https://github.com/huggingface/datasets/blob/main/src/datasets/features/nifti.py)
