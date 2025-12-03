# OOM Root Cause Analysis

> Why uploads crash at 0% with "leaked semaphore" warnings.

---

## Executive Summary

The crash is caused by a **design limitation in the HuggingFace `datasets` library**. When uploading large datasets with embedded files, the library accumulates ALL shard bytes (~270 GB) in RAM before finalizing the commit, triggering the OS OOM killer.

The "semaphore leak" warning is a symptom, not the cause. The `tmux` environment is irrelevant.

**Status**: Fixed in `arc-bids` via custom memory-safe uploader.

---

## The Root Cause

Inside `datasets/arrow_dataset.py`, the `_push_parquet_shards_to_hub` function has a fatal flaw:

```python
additions = []
for shard in shards:
    parquet_content = shard.to_parquet_bytes()  # ~300 MB
    shard_addition = CommitOperationAdd(path_or_fileobj=parquet_content)
    api.preupload_lfs_files(additions=[shard_addition])
    additions.append(shard_addition)  # THE BUG: keeps bytes alive
```

The `additions` list holds references to every `CommitOperationAdd` object, which contains the full Parquet byte-string. Python cannot garbage collect them.

**Result**: 902 shards × 300 MB = ~270 GB RAM requested → OOM.

---

## Investigated Causes

| Cause | Certainty | Verdict |
|-------|-----------|---------|
| Memory accumulation in `additions` list | 100% | **Primary cause** |
| Semaphore leak warning | High | Symptom of OOM kill |
| macOS `spawn` overhead | Medium | Minor contributor |
| tmux vs shell differences | Low | Coincidence |
| Git LFS buffering | Low | Not significant |

### 1. Memory accumulation (primary cause)

- Each shard is ~300 MB of Parquet bytes
- All 902 shards are kept in `additions` list
- Memory grows linearly until crash
- The `preupload_lfs_files` call succeeds but doesn't release memory

### 2. Semaphore leak (symptom)

When the OS kills the process due to OOM:
- Child processes/thread pools are terminated abruptly
- `multiprocessing.resource_tracker` sees unreleased semaphores
- Prints the `UserWarning` about "leaked semaphore objects"

This is a **symptom** of the crash, not the cause.

### 3. macOS spawn overhead (minor)

- macOS uses `spawn` for multiprocessing (higher memory per process than `fork`)
- Internal calls might spawn threads/processes
- Lowers the OOM threshold slightly but not the main issue

### 4. tmux differences (irrelevant)

- `tmux` has the same `ulimit` as the main shell
- Previous "successes" were likely dry runs or smaller subsets
- The OOM killer behavior is the same

### 5. Git LFS buffering (not significant)

- `huggingface_hub` might buffer uploads if network is slow
- But `CommitOperationAdd` holding bytes is the dominant factor

---

## Technical Evidence

**File**: `.venv/lib/python3.13/site-packages/datasets/arrow_dataset.py`
**Function**: `_push_parquet_shards_to_hub`
**Lines**: ~5551-5554

```python
# Creates object holding FULL shard bytes
shard_addition = CommitOperationAdd(
    path_in_repo=shard_path_in_repo,
    path_or_fileobj=parquet_content  # <-- bytes, not path
)

# Uploads succeed
api.preupload_lfs_files(..., additions=[shard_addition], ...)

# THE BUG: appends to list, keeping bytes alive forever
additions.append(shard_addition)

# Loop continues 902 times... RAM grows until crash
```

---

## The Fix

We implemented a **custom memory-safe uploader** in `src/arc_bids/core.py`:

```python
for i in range(num_shards):
    shard = ds.shard(num_shards=num_shards, index=i, contiguous=True)
    # Get raw PyArrow table and embed external files
    table = shard._data.table
    embedded_table = embed_table_storage(table)
    # Write with PyArrow directly (not datasets)
    pq.write_table(embedded_table, local_parquet_path)
    api.upload_file(path_or_fileobj=str(local_parquet_path), ...)
    local_parquet_path.unlink()  # Free disk
    del shard  # Free RAM
```

**Key differences**:

1. **One shard at a time**: Process, upload, delete, repeat
2. **Direct Arrow table access**: `shard._data.table` gives raw `pyarrow.Table`
3. **Correct embedding**: `embed_table_storage(table)` expects Arrow table, NOT batches
4. **File path, not bytes**: `upload_file(path=...)` streams from disk
5. **Aggressive cleanup**: Delete temp file and dereference before next shard

**Result**: Memory usage is constant (~1 GB) instead of linear (270 GB).

---

## Implementation Bug (Fixed)

Our initial fix had a bug: we called `embed_table_storage` via `.map()`:

```python
# WRONG - .map() passes dict batches, not Arrow tables
shard = shard.map(embed_table_storage, batched=True)
```

`embed_table_storage` signature: `(table: pyarrow.Table) -> pyarrow.Table`

It expects a full Arrow table, not dictionary batches from `.map()`. This caused
the process to crash with the same semaphore leak symptom.

**Fix**: Call `embed_table_storage` directly on the Arrow table:

```python
# CORRECT - pass Arrow table directly
table = shard._data.table
embedded_table = embed_table_storage(table)
pq.write_table(embedded_table, path)
```

---

## Related

- [Why Uploads Fail](why-uploads-fail.md) - The broader context
- [Fix OOM Crashes](../how-to/fix-oom-crashes.md) - How to use the fix
- [Architecture Decisions](architecture.md) - Design rationale
