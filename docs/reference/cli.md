# CLI Reference

> Command-line interface for arc-bids.

---

## Installation

```bash
uv add arc-bids
# or
pip install arc-bids
```

---

## Commands

### `arc-bids build`

Build and upload a BIDS dataset to HuggingFace Hub.

```bash
arc-bids build <bids_root> --hf-repo <repo_id> [options]
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `bids_root` | Path to the BIDS dataset root directory |

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--hf-repo` | Required | HuggingFace repo ID (e.g., `org/dataset-name`) |
| `--dry-run` | False | Build dataset locally without pushing to Hub |
| `--no-dry-run` | - | Explicitly disable dry run (push to Hub) |

#### Examples

```bash
# Dry run (build locally, don't upload)
arc-bids build data/openneuro/ds004884 --hf-repo hugging-science/arc-aphasia-bids

# Full upload
arc-bids build data/openneuro/ds004884 --hf-repo hugging-science/arc-aphasia-bids --no-dry-run
```

#### Output

```
Processing ARC dataset from: data/openneuro/ds004884
Target HF repo: hugging-science/arc-aphasia-bids
Dry run: False
Building file table...
File table has 902 rows
Building HF dataset...
Pushing to Hub with num_shards=902 to prevent OOM
Uploading the dataset shards:   5%|█▌        | 45/902 [02:15<42:30, 3.0s/shard]
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HF_TOKEN` | HuggingFace API token (alternative to `huggingface-cli login`) |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (check stderr for details) |

---

## Related

- [Tutorial: First Upload](../tutorials/first-upload.md)
- [Python API](api.md)
