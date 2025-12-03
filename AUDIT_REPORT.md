# Pipeline Audit Report

**Date**: 2025-12-03
**Auditor**: Claude Code
**Repository**: arc-aphasia-bids
**Purpose**: Identify latent bugs, missing best practices, and improvement opportunities

---

## Executive Summary

**Overall Status**: Production-Ready with Minor Improvements Recommended

The codebase is well-structured, thoroughly documented, and has successfully uploaded a 293GB neuroimaging dataset to HuggingFace Hub. The implementation correctly works around known upstream bugs in the `datasets` library. No critical bugs were found during this audit.

| Category | Status |
|----------|--------|
| Tests | 45/45 passing |
| Type Safety | mypy passes (0 errors) |
| Lint | ruff passes (0 errors) |
| Coverage | 86% |
| Documentation | Comprehensive |

---

## Issues Found

### P1 - Important

#### 1. Unstable Git Dependency for `datasets`

**Location**: `pyproject.toml:88-89`

```toml
[tool.uv.sources]
datasets = { git = "https://github.com/huggingface/datasets.git" }
```

**Problem**: The project depends on HuggingFace datasets main branch (unstable). The [datasets 4.0.0 release](https://github.com/huggingface/datasets/issues/7676) (July 2025) introduced breaking changes including:
- Removal of `List` feature type in favor of `LargeList`
- Changes to Audio/Image feature casting
- Various dataset compatibility issues

**Risk**: Any push to `datasets` main could break this project without warning.

**Recommendation**:
- If the original bug is fixed in PyPI stable (3.x), switch back to version pinning
- If git is still required, pin to a specific commit hash:
  ```toml
  datasets = { git = "https://github.com/huggingface/datasets.git", rev = "abc123" }
  ```

---

### P2 - Medium

#### 2. Unused Pydantic Dependency

**Location**: `pyproject.toml:32`

```toml
dependencies = [
    ...
    "pydantic>=2.0.0",
]
```

**Problem**: Pydantic is declared as a dependency but is **never imported or used** anywhere in the codebase. All data classes use Python's built-in `dataclasses` module, which is appropriate for this use case.

**Impact**:
- Unnecessary ~2MB dependency bloat
- Potential confusion for contributors
- Extra CI time

**Recommendation**: Remove `pydantic>=2.0.0` from dependencies. The existing `@dataclass` usage is correct and sufficient.

---

### P3 - Minor

#### 3. No Network Retry Logic in Upload

**Location**: `src/arc_bids/core.py:254-264`

```python
try:
    api.upload_file(
        path_or_fileobj=str(local_parquet_path),
        ...
    )
except Exception:
    logger.exception("Failed to upload shard %d", i)
    raise
```

**Problem**: For a 902-shard upload (293GB), network hiccups are likely. A single failed request aborts the entire process with no retry.

**Recommendation**: Add exponential backoff retry:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2))
def _upload_with_retry(...):
    ...
```

#### 4. Missing Integration Test for Real Embedding

**Location**: `tests/test_core_nifti.py`

**Problem**: The custom sharding logic in `push_dataset_to_hub` (which was critical for the OOM fix) is only tested with mocks. The actual `embed_table_storage` → `pq.write_table` → `api.upload_file` path isn't tested with real data.

**Recommendation**: Add a small integration test that:
- Creates a 2-3 row dataset with real tiny NIfTI files
- Actually calls `embed_table_storage` (not mocked)
- Verifies the parquet file is valid

---

### P4 - Informational

#### 5. Hardcoded Expected Counts in Validation

**Location**: `src/arc_bids/validation.py:97-107`

```python
EXPECTED_COUNTS = {
    "subjects": 230,
    "sessions": 902,
    "t1w_series": 441,
    ...
}
```

**Problem**: These counts are from the Sci Data paper (Gibson et al., 2024). If OpenNeuro dataset ds004884 is updated, these will be stale.

**Note**: This is acceptable since the dataset version is pinned (v1.0.1), but consider adding a comment noting the source version.

#### 6. No Resume Capability for Interrupted Uploads

**Location**: `src/arc_bids/core.py` (entire `push_dataset_to_hub` function)

**Problem**: If upload is interrupted at shard 450/902, there's no way to resume. The user must restart from scratch.

**Note**: This is a "nice to have" - the current implementation is correct. Adding resume would require tracking uploaded shards (e.g., checking HF Hub before upload).

---

## Things That Are NOT Issues

### Pydantic Not Needed

**Question raised**: Should Pydantic be incorporated?

**Answer**: No. The current dataclass usage is correct:

1. **`DatasetBuilderConfig`** - Simple config container with 4 fields, no validation needed
2. **`BidsDatasetConfig`** - Simple config with 3 fields
3. **`ValidationCheck`** / **`ValidationResult`** - Simple containers for results

Pydantic would be overkill here. It's useful when you need:
- Complex nested validation
- JSON Schema generation
- API request/response models
- Type coercion from strings

This pipeline reads well-structured BIDS data (already validated by BIDS spec) and doesn't need Pydantic's overhead.

### Test Coverage

86% coverage is good for this type of project. The uncovered lines are:
- CLI command execution (hard to test without subprocess)
- BIDS validator integration (requires `npx`)
- Some edge cases in validation

### Upstream Bugs

The codebase already correctly works around two known HuggingFace bugs (documented in `UPSTREAM_BUG_ANALYSIS.md`):
1. Memory accumulation in `_push_parquet_shards_to_hub`
2. `embed_table_storage` crash on sharded `Sequence(Nifti())`

---

## Best Practices Checklist

| Practice | Status | Notes |
|----------|--------|-------|
| Type hints everywhere | Yes | mypy strict mode passes |
| Docstrings | Yes | Google-style, comprehensive |
| Tests | Yes | 45 tests, 86% coverage |
| Linting | Yes | ruff configured |
| Pre-commit hooks | Yes | Configured |
| CI/CD | Partial | No GitHub Actions found |
| Error handling | Yes | Appropriate exceptions |
| Logging | Yes | Uses `logging` module |
| Documentation | Yes | README, CLAUDE.md, docs/ |

---

## Recommended Actions

### Immediate (Before Next Use)

1. **Check if datasets bug is fixed**: Test with `datasets>=3.5.0` from PyPI instead of git main
2. **Remove unused pydantic dependency**: One-line deletion from pyproject.toml

### Future Improvements

3. **Pin git dependency to commit**: If git is still needed, pin to specific commit
4. **Add retry logic**: Use tenacity for upload retries
5. **Add GitHub Actions CI**: Automate test/lint on PR

---

## Validation Performed

```bash
# All passed
uv run pytest                    # 45/45 tests passing
uv run mypy src tests            # Success: no issues in 11 files
uv run ruff check .              # All checks passed
```

---

## References

- [HuggingFace datasets 4.0 breaking changes](https://github.com/huggingface/datasets/issues/7676)
- [HuggingFace datasets Nifti documentation](https://huggingface.co/docs/datasets/en/nifti_dataset)
- [embed_table_storage issues](https://github.com/huggingface/datasets/issues/5717)
- [BIDS specification](https://bids-specification.readthedocs.io/)

---

*Report generated by Claude Code audit on 2025-12-03*
