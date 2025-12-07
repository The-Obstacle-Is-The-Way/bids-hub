# Phase 00: Overview & Execution Order

> Status: MASTER INDEX
> Purpose: Map of all specs and execution order

---

## What We're Building

**Core Infrastructure** (should go upstream to `datasets` library):
- `build_hf_dataset()` - Convert file table → HF Dataset
- `push_dataset_to_hub()` - Memory-safe sharded upload
- `ValidationCheck` / `ValidationResult` - Generic validation framework
- Workarounds for upstream bugs (#7894, #7893)

**Dataset Scripts** (what researchers write per-dataset):
- Schema definition (`get_{dataset}_features()`)
- File discovery (`build_{dataset}_file_table()`)
- Expected counts for validation
- Download scripts

---

## Execution Order

| Phase | Spec File | Description | Blocking? |
|-------|-----------|-------------|-----------|
| 01 | `01-isles24-upload.md` | Upload ISLES24 NOW (no refactor) | **YES** |
| 02 | `02-validation-refactor.md` | Extract generic validation | No |
| 03 | `03-scripts-reorganize.md` | Namespace scripts by dataset | No |
| 04 | `04-src-reorganize.md` | Create datasets/ subdirectory | No |
| 05 | `05-docs-cleanup.md` | Dataset cards, consolidate docs | No |
| 06 | `06-root-files.md` | README, pyproject.toml updates | No |
| 07 | `07-upstream-contrib.md` | Future: contribute core to HF | Future |

---

## Current State

```
src/arc_bids/
├── __init__.py          # Exports (needs update after refactor)
├── core.py              # GENERIC ✅ (keep as-is)
├── config.py            # ARC config (minor)
├── arc.py               # ARC-specific ✅
├── isles24.py           # ISLES24-specific ✅
├── validation.py        # MIXED ❌ (needs split)
└── cli.py               # CLI (needs isles24 validate)

scripts/
├── download_arc.sh      # ARC only
├── validate_download.py # ARC only (naming unclear)
└── validate_hf_download.py # ARC only (naming unclear)

docs/
├── dataset-cards/       # EMPTY ❌
├── explanation/
├── how-to/
├── reference/
└── tutorials/
```

---

## Target State

```
src/arc_bids/
├── __init__.py
├── cli.py
│
├── core/                    # GENERIC (upstream candidate)
│   ├── __init__.py
│   ├── builder.py           # build_hf_dataset, push_dataset_to_hub
│   ├── config.py            # DatasetBuilderConfig
│   └── utils.py             # find_single_nifti, find_all_niftis
│
├── validation/              # GENERIC + SPECIFIC
│   ├── __init__.py
│   ├── base.py              # ValidationCheck, ValidationResult
│   ├── arc.py               # ARC expected counts + validate()
│   └── isles24.py           # ISLES24 expected counts + validate()
│
└── datasets/                # DATASET-SPECIFIC
    ├── __init__.py
    ├── arc.py               # build_arc_file_table, get_arc_features
    └── isles24.py           # build_isles24_file_table, get_isles24_features

scripts/
├── arc/
│   ├── download.sh
│   ├── validate_download.py
│   └── validate_hf_upload.py
└── isles24/
    ├── download.sh
    ├── validate_download.py
    └── validate_hf_upload.py

docs/
├── dataset-cards/
│   ├── arc-aphasia-bids.md
│   └── isles24-stroke.md
└── ...
```

---

## Rules

1. **One spec = one PR** (ideally)
2. **Tests before refactor** - Ensure coverage before moving code
3. **Phase 01 is blocking** - Upload ISLES24 before any refactoring
4. **Backward compatibility** - Re-export moved symbols in `__init__.py`
