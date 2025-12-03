# Draft: Upstream Issues for huggingface/datasets

**Status**: DRAFT - Do not open yet
**Prepared**: 2025-12-02

---

## Related Open Issues to Link

### For Bug 1 (Memory Accumulation)

| Issue | Title | Relevance |
|-------|-------|-----------|
| [#5990](https://github.com/huggingface/datasets/issues/5990) | Pushing a large dataset on the hub consistently hangs | **HIGHLY RELATED** - Same root cause, 46 comments, open since 2023 |
| [#7400](https://github.com/huggingface/datasets/issues/7400) | 504 Gateway Timeout when uploading large dataset | Related - large upload failures |
| [#6686](https://github.com/huggingface/datasets/issues/6686) | Question: Is there any way for uploading a large image dataset? | Related - Sequence(Image()) upload issues |

### For Bug 2 (Embed Crash)

| Issue | Title | Relevance |
|-------|-------|-----------|
| [#6790](https://github.com/huggingface/datasets/issues/6790) | PyArrow 'Memory mapping file failed' | Potentially related - PyArrow memory issues |
| [#7852](https://github.com/huggingface/datasets/issues/7852) | Problems with NifTI | Related - NIfTI embedding issues (CLOSED, fixed by #7853) |

### Relevant Open PRs

| PR | Title | Status | Relevance |
|----|-------|--------|-----------|
| [#6056](https://github.com/huggingface/datasets/pull/6056) | Implement proper checkpointing for dataset uploading | OPEN (since 2023!) | Addresses #5990, but NOT the memory accumulation root cause |

---

## Issue 1: Memory Accumulation

### Proposed Title
`push_to_hub` OOM: `_push_parquet_shards_to_hub` accumulates all shard bytes in memory

### Key Points for Human-Sounding Issue

1. **Lead with the symptom** - "Upload crashes/hangs at X%"
2. **Reference existing issues** - #5990 has 46 comments of frustrated users
3. **Provide root cause** - Point to exact code location
4. **Offer working solution** - Our workaround proves it's fixable
5. **Don't be preachy** - State facts, not opinions

### Draft Body

```markdown
### Problem

Large dataset uploads crash or hang due to memory exhaustion. This appears to be
the root cause of #5990 (46 comments, open since 2023).

### Root Cause

In `_push_parquet_shards_to_hub`, the `additions` list accumulates every
`CommitOperationAdd` with full Parquet bytes:

```python
additions = []
for shard in shards:
    parquet_content = shard.to_parquet_bytes()  # ~300 MB per shard
    shard_addition = CommitOperationAdd(path_or_fileobj=parquet_content)
    api.preupload_lfs_files(additions=[shard_addition])
    additions.append(shard_addition)  # Bytes stay in memory
```

For a 902-shard dataset: 902 × 300 MB = ~270 GB RAM → OOM.

### Reproduction

1. Create a dataset with embedded files (Image, Audio, Nifti, etc.)
2. Call `push_to_hub()` with many shards
3. Watch memory grow linearly until crash

### Workaround

Process one shard at a time, upload via `HfApi.upload_file(path=...)`, delete before next:

```python
for i in range(num_shards):
    shard = ds.shard(num_shards=num_shards, index=i)
    shard.to_parquet(local_path)
    api.upload_file(path_or_fileobj=str(local_path), ...)
    local_path.unlink()
    del shard
```

### Suggested Fix

After `preupload_lfs_files` succeeds, release the bytes - either by:
- Clearing `parquet_content` from the `CommitOperationAdd`
- Streaming from disk instead of holding in memory
- Committing incrementally

### Environment

- datasets: main (post-0.22.0)
- Platform: macOS ARM64
- Python: 3.13
- Dataset: 902 shards, ~270 GB embedded NIfTI files

Related: #5990, #7400, #6686
```

---

## Issue 2: Embed Crash on Sharded Datasets

### Proposed Title
`embed_table_storage` crashes (SIGKILL) on sharded datasets with `Sequence()` nested types

### Key Points

1. **Distinct from Bug 1** - Even with memory fixed, this crashes
2. **Specific trigger** - `ds.shard()` + `Sequence(Nifti/Image/Audio)`
3. **No Python traceback** - C++ level crash
4. **Workaround exists** - Pandas round-trip

### Draft Body

```markdown
### Problem

`embed_table_storage` crashes with SIGKILL when processing sharded datasets
containing `Sequence()` nested types (e.g., `Sequence(Nifti())`, likely affects
`Sequence(Image())` and `Sequence(Audio())` too).

### Reproduction

```python
from datasets import Dataset, Features, Sequence, Value
from datasets.features import Nifti
from datasets.table import embed_table_storage

features = Features({
    "id": Value("string"),
    "images": Sequence(Nifti()),
})

ds = Dataset.from_dict({
    "id": ["a", "b"],
    "images": [["/path/to/file.nii.gz"], []],
}).cast(features)

# Works:
table = ds._data.table.combine_chunks()
embed_table_storage(table)  # OK

# Crashes:
shard = ds.shard(num_shards=2, index=0)
shard_table = shard._data.table.combine_chunks()
embed_table_storage(shard_table)  # SIGKILL - no traceback
```

### Observations

- Crash is at C++ level (no Python traceback)
- `ds.select([i])` also crashes (not just `shard()`)
- Crashes even when the Sequence is an empty list
- Single (non-Sequence) Nifti columns work fine
- Manually created datasets work; only sharded/selected ones crash

### Workaround

Convert to pandas and recreate the Dataset:

```python
shard_df = shard.to_pandas()
fresh = Dataset.from_pandas(shard_df, preserve_index=False)
fresh = fresh.cast(ds.features)
# Now embedding works
```

### Hypothesis

`ds.shard()`/`ds.select()` creates Arrow table views with internal references
that cause issues when `embed_table_storage` processes nested struct types.

### Environment

- datasets: main (post-0.22.0)
- Platform: macOS ARM64 (may be platform-specific?)
- Python: 3.13
- PyArrow: 18.1.0

Related: #7852 (NIfTI embedding, now fixed)
```

---

## Strategy

1. **Issue 1** should reference #5990 heavily - show we found the root cause
2. **Issue 2** is more exploratory - may be PyArrow bug surfacing through datasets
3. Open issues first, then PRs that reference them
4. PRs come from your fork with working code

---

## Checklist Before Opening

- [ ] Upload completes successfully (proves our fix works)
- [ ] Verify workaround code snippets are accurate
- [ ] Double-check issue numbers to link
- [ ] Tone check: helpful, not ranty
