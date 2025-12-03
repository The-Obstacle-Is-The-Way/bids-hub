# How to Fix OOM Crashes on Large Datasets

> **Problem**: Upload crashes at 0% with "leaked semaphore" warning
> **Solution**: Use `arc-bids` which has a custom memory-safe uploader

---

## Symptoms

```text
Uploading the dataset shards:   0%|          | 0/902 [00:00<?, ? shards/s]
UserWarning: resource_tracker: There appear to be 1 leaked semaphore objects
[Process killed]
```

The upload crashes at 0% even WITH `num_shards` set.

---

## Root Cause

The `datasets` library has a bug: it accumulates ALL shard byte-strings in memory before finalizing the upload, even when using `num_shards`. For 902 shards × ~300 MB = ~270 GB RAM → OOM.

See [OOM Root Cause Analysis](../explanation/oom-root-cause.md) for full details.

---

## Solution: Use arc-bids CLI

The `arc-bids` package includes a custom memory-safe uploader that bypasses this bug:

```bash
# Build and upload (memory-safe)
uv run arc-bids build data/openneuro/ds004884 \
    --hf-repo hugging-science/arc-aphasia-bids \
    --no-dry-run
```

Memory usage stays constant (~1-2 GB) regardless of dataset size.

---

## How It Works

Our `push_dataset_to_hub()` function works around **two upstream bugs**:

1. **Bug 1 (Memory accumulation)**: Process one shard at a time, upload, delete
2. **Bug 2 (Arrow crash)**: Convert shard to pandas and back before embedding

Steps:

1. **Iterates one shard at a time**
2. **Converts to pandas and recreates Dataset** (breaks internal Arrow references)
3. **Embeds NIfTI bytes into Arrow table** (only for current shard)
4. **Writes to temporary Parquet file on disk**
5. **Uploads via `HfApi.upload_file(path=...)` - streams from disk, not RAM**
6. **Deletes temp file and dereferences shard before next iteration**

```python
# From src/arc_bids/core.py
for i in range(num_shards):
    shard = ds.shard(num_shards=num_shards, index=i, contiguous=True)

    # CRITICAL: Convert to pandas and back to break internal Arrow references
    # that cause crashes in embed_table_storage on Sequence(Nifti()) columns
    shard_df = shard.to_pandas()
    fresh_shard = Dataset.from_pandas(shard_df, preserve_index=False)
    fresh_shard = fresh_shard.cast(ds.features)

    # Now embed and write
    table = fresh_shard._data.table.combine_chunks()
    embedded_table = embed_table_storage(table)
    pq.write_table(embedded_table, str(local_parquet_path))

    api.upload_file(path_or_fileobj=str(local_parquet_path), ...)
    local_parquet_path.unlink()  # Free disk
    del fresh_shard, shard_df, shard  # Free RAM
```

---

## If You're Not Using arc-bids

If you need this pattern for a different dataset, copy the approach from `src/arc_bids/core.py`:

1. Don't use `ds.push_to_hub()` for large embedded datasets
2. Manually shard with `ds.shard()`
3. **Convert shard to pandas and recreate Dataset** (critical for `Sequence(Nifti())`)
4. Embed with `embed_table_storage(table)`
5. Write to Parquet on disk with `pq.write_table()`
6. Upload with `HfApi.upload_file(path=...)` (file path, not bytes)
7. Clean up before next shard

See [UPSTREAM_BUG_ANALYSIS.md](/UPSTREAM_BUG_ANALYSIS.md) for full technical details.

---

## Verification

After running the upload, you should see steady progress:

```text
Uploading Shards:  50%|█████     | 451/902 [2:15:30<2:10:00, 8.65s/it]
```

Memory usage stays flat at ~1-2 GB instead of growing linearly.

---

## Related

- [OOM Root Cause Analysis](../explanation/oom-root-cause.md) - Technical deep-dive
- [Why Uploads Fail](../explanation/why-uploads-fail.md) - Full explanation
- [Fix Empty Uploads](fix-empty-uploads.md) - Another common issue
