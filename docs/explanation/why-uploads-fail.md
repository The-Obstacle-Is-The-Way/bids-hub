# Why Large NIfTI Uploads Fail

> Understanding the root causes of upload failures so you can avoid them.

This document explains **why** HuggingFace dataset uploads fail with large NIfTI files. For solutions, see the [How-to Guides](../how-to/).

---

## The "Metadata Trap"

The fundamental problem is a **size estimation mismatch**.

### What the Library Sees

When you create a dataset from a DataFrame:

```python
file_table = pd.DataFrame({
    "subject_id": ["sub-001", "sub-002", ...],  # 902 rows
    "t1w": ["/path/to/file1.nii.gz", ...],      # Strings, not bytes
})

ds = Dataset.from_pandas(file_table)
```

The `datasets` library estimates the dataset size by looking at the DataFrame:
- 902 rows of text strings
- **Estimated size: ~1 MB**

### What Actually Gets Uploaded

When you call `push_to_hub(embed_external_files=True)`:

1. The library reads each file path
2. Opens the actual NIfTI file
3. Embeds the binary content into Parquet

For a real neuroimaging dataset:

| Modality | Count | Typical Size | Total |
|----------|-------|--------------|-------|
| T1w | 447 | ~10 MB | ~4.5 GB |
| T2w | 441 | ~10 MB | ~4.4 GB |
| FLAIR | 235 | ~10 MB | ~2.4 GB |
| BOLD fMRI | 1,402 | ~150 MB | **~210 GB** |
| DWI | 2,089 | ~30 MB | ~63 GB |
| sbref | 322 | ~5 MB | ~1.6 GB |
| Lesion masks | 228 | ~1 MB | ~0.2 GB |
| **Total** | **5,164** | - | **~273 GB** |

**The library is tricked into thinking it's uploading 1 MB when it's actually 273 GB.**

### The Fatal Decision

The library uses a heuristic to decide shard count:

```
If estimated_size < default_shard_size (500 MB):
    num_shards = 1
```

Since 1 MB < 500 MB, it creates **one single shard** for the entire dataset.

When embedding starts, it tries to buffer 273 GB into that single shard → OOM crash.

---

## Why `max_shard_size` Doesn't Help

You might think: "I'll just set `max_shard_size='500MB'`"

This doesn't work because of how size estimation happens:

> "we don't always embed image bytes in the underlying arrow table, which can lead to bad size estimation (we use the first 1000 table rows to estimate the external file size)"
>
> — [HuggingFace Issue #5386](https://github.com/huggingface/datasets/issues/5386)

The library samples the first 1000 rows to estimate average row size. But:
- File sizes vary wildly (1.7 MB to 804.8 MB per session in our data)
- The sample may not be representative
- External file sizes aren't known until embedding time

**Result**: Shards that are supposed to be 500 MB end up being 2+ GB.

---

## Why the Stable Release Has Empty Uploads

The stable PyPI release of `datasets` has a bug in `Nifti.embed_storage`.

When you call:
```python
ds.push_to_hub(..., embed_external_files=True)
```

The embedding logic fails to properly read and include NIfTI bytes. The upload "succeeds" but parquet files contain no actual image data.

**This is a silent failure** - no error is raised. You only discover it when loading the dataset and finding empty files.

The fix exists in the GitHub main branch but hasn't been released to PyPI yet (as of Dec 2025).

---

## The Session Size Distribution

Real data from the ARC dataset (902 sessions):

```
LARGEST SESSIONS:
  sub-M2168/ses-1148: 804.8 MB (11 files)
  sub-M2094/ses-4625: 802.7 MB (11 files)
  sub-M2118/ses-4363: 794.7 MB (9 files)

SMALLEST SESSIONS:
  sub-M2029/ses-395:  3.8 MB (1 file)
  sub-M2221/ses-772:  3.4 MB (1 file)
  sub-M2191/ses-1359: 1.7 MB (2 files)

STATISTICS:
  Total: 272.8 GB
  Average: 309.7 MB per session
  Range: 1.7 MB to 804.8 MB
```

This 470x variance in session size is why `max_shard_size` fails - no fixed threshold works.

---

## Why `num_shards` Is the Solution

Explicit sharding bypasses all the estimation problems:

```python
ds.push_to_hub(
    repo_id,
    embed_external_files=True,
    num_shards=902,  # One per session
)
```

| Aspect | Before | After |
|--------|--------|-------|
| Shards | 1 | 902 |
| RAM needed | 273 GB | ~805 MB max |
| Estimation | Based on strings | N/A (explicit) |
| Result | OOM crash | Success |

### Why One Shard Per Session?

1. **Memory bounded**: Largest session is 805 MB, safe on any machine
2. **Logically coherent**: 1 shard = 1 session = 1 logical unit
3. **HF Hub compliant**: All shards < 200 GB limit, < 50 GB recommended
4. **Parallelizable**: Can be processed independently

---

## Summary of Failure Modes

| Failure | Root Cause | Fix |
|---------|------------|-----|
| OOM at 0% | Size estimation from paths, not bytes | `num_shards=N` |
| Empty files | Bug in stable `datasets` release | Install from git |
| Huge shards | `max_shard_size` uses bad estimates | Use `num_shards` instead |
| Silent failures | No validation before upload | Test locally first |

---

## References

- [HuggingFace Issue #5386](https://github.com/huggingface/datasets/issues/5386): `max_shard_size` breaks with large files
- [HuggingFace Issue #5990](https://github.com/huggingface/datasets/issues/5990): Large dataset uploads hang
- [HuggingFace Forum](https://discuss.huggingface.co/t/any-workaround-for-push-to-hub-limits/59274): push_to_hub limits discussion

---

## Related

- [Fix OOM Crashes](../how-to/fix-oom-crashes.md) - The solution
- [Fix Empty Uploads](../how-to/fix-empty-uploads.md) - The other major pitfall
- [Architecture Decisions](architecture.md) - Why we designed it this way
