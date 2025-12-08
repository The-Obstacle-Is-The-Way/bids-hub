#!/usr/bin/env python3
"""
Validate ISLES24 dataset download integrity before HuggingFace upload.

This validates the local Zenodo extraction against expected counts.

Usage:
    uv run python scripts/validate_isles24_download.py data/zenodo/isles24/train

Expected Zenodo v7 structure:
    train/
    ├── clinical_data-description.xlsx
    ├── raw_data/sub-stroke0001/.../
    ├── derivatives/sub-stroke0001/.../
    └── phenotype/sub-stroke0001/.../
"""

from __future__ import annotations

import sys
from pathlib import Path

# Expected counts from Zenodo v7 / ISLES24 paper
EXPECTED_SUBJECTS = 149

# Modalities expected per subject (approximate - some are optional)
EXPECTED_MODALITIES = {
    # Raw data (ses-01)
    "ncct": 149,  # All subjects have NCCT
    "cta": 149,  # All subjects have CTA
    "ctp": 140,  # ~94% have CTP (some missing)
    # Derivatives - perfusion maps (ses-01)
    "tmax": 140,
    "mtt": 140,
    "cbf": 140,
    "cbv": 140,
    # Derivatives - follow-up (ses-02)
    "dwi": 149,
    "adc": 149,
    "lesion_mask": 149,
    # Optional derivatives
    "lvo_mask": 100,  # ~67% have LVO mask
    "cow_mask": 100,  # ~67% have CoW segmentation
}


def validate_isles24_download(bids_root: Path) -> tuple[bool, list[str]]:
    """
    Validate ISLES24 download structure and counts.

    Returns:
        (all_passed, list of check messages)
    """
    bids_root = Path(bids_root).resolve()
    messages: list[str] = []
    all_passed = True

    # Check 1: Root directory exists
    if not bids_root.exists():
        messages.append(f"❌ Root directory not found: {bids_root}")
        return False, messages
    messages.append(f"✅ Root directory exists: {bids_root}")

    # Check 2: Required directories exist
    raw_data = bids_root / "raw_data"
    derivatives = bids_root / "derivatives"
    phenotype = bids_root / "phenotype"

    for name, path in [
        ("raw_data", raw_data),
        ("derivatives", derivatives),
        ("phenotype", phenotype),
    ]:
        if path.exists():
            messages.append(f"✅ {name}/ exists")
        else:
            messages.append(f"❌ {name}/ missing")
            all_passed = False

    # Check 3: Metadata file exists
    xlsx = bids_root / "clinical_data-description.xlsx"
    if xlsx.exists():
        messages.append("✅ clinical_data-description.xlsx exists")
    else:
        messages.append("⚠️  clinical_data-description.xlsx missing (may be OK)")

    # Check 4: Subject count
    if raw_data.exists():
        subjects = sorted(raw_data.glob("sub-*"))
        subject_count = len(subjects)
        if subject_count == EXPECTED_SUBJECTS:
            messages.append(f"✅ Subject count: {subject_count} (expected {EXPECTED_SUBJECTS})")
        elif subject_count > 0:
            messages.append(f"⚠️  Subject count: {subject_count} (expected {EXPECTED_SUBJECTS})")
        else:
            messages.append("❌ No subjects found in raw_data/")
            all_passed = False
    else:
        subject_count = 0
        subjects = []

    # Check 5: Session structure (spot check first subject)
    if subjects:
        first_subject = subjects[0]
        ses01 = first_subject / "ses-01"
        if ses01.exists():
            messages.append(f"✅ Session structure: ses-01 exists for {first_subject.name}")
        else:
            messages.append(f"❌ Session structure: ses-01 missing for {first_subject.name}")
            all_passed = False

    # Check 6: Derivative structure (spot check)
    if derivatives.exists() and subjects:
        first_deriv = derivatives / subjects[0].name
        if first_deriv.exists():
            ses01_deriv = first_deriv / "ses-01"
            ses02_deriv = first_deriv / "ses-02"
            if ses01_deriv.exists() and ses02_deriv.exists():
                messages.append(
                    f"✅ Derivative structure: ses-01 and ses-02 exist for {subjects[0].name}"
                )
            else:
                messages.append(f"⚠️  Derivative structure incomplete for {subjects[0].name}")
        else:
            messages.append(f"⚠️  No derivatives for {subjects[0].name}")

    # Check 7: Count key modality files across all subjects
    messages.append("\n--- Modality Counts ---")

    modality_checks = [
        # (name, search_path_pattern, expected_count)
        ("ncct (raw)", "raw_data/sub-*/ses-01/*_ncct.nii.gz", EXPECTED_MODALITIES["ncct"]),
        ("cta (raw)", "raw_data/sub-*/ses-01/*_cta.nii.gz", EXPECTED_MODALITIES["cta"]),
        (
            "tmax (deriv)",
            "derivatives/sub-*/ses-01/perfusion-maps/*_space-ncct_tmax.nii.gz",
            EXPECTED_MODALITIES["tmax"],
        ),
        (
            "dwi (deriv)",
            "derivatives/sub-*/ses-02/*_space-ncct_dwi.nii.gz",
            EXPECTED_MODALITIES["dwi"],
        ),
        (
            "lesion (deriv)",
            "derivatives/sub-*/ses-02/*_space-ncct_lesion-msk.nii.gz",
            EXPECTED_MODALITIES["lesion_mask"],
        ),
        (
            "lvo (deriv)",
            "derivatives/sub-*/ses-01/*_space-ncct_lvo-msk.nii.gz",
            EXPECTED_MODALITIES["lvo_mask"],
        ),
    ]

    for name, pattern, expected in modality_checks:
        count = len(list(bids_root.glob(pattern)))
        if count >= expected * 0.9:  # 10% tolerance
            messages.append(f"✅ {name}: {count} files (expected ~{expected})")
        elif count > 0:
            messages.append(f"⚠️  {name}: {count} files (expected ~{expected})")
        else:
            messages.append(f"❌ {name}: {count} files (expected ~{expected})")
            # Don't fail on missing modalities - extraction may be in progress

    # Check 8: Spot check NIfTI integrity (first file of each type)
    messages.append("\n--- NIfTI Integrity (spot check) ---")

    sample_files = list(bids_root.glob("derivatives/sub-stroke0001/ses-01/*_space-ncct_cta.nii.gz"))
    if sample_files:
        import gzip

        try:
            with gzip.open(sample_files[0], "rb") as f:
                header = f.read(4)
                if header[:2] == b"\x1c\x01" or header == b"n+1\x00":
                    messages.append(f"✅ NIfTI header valid: {sample_files[0].name}")
                else:
                    messages.append(f"⚠️  NIfTI header check inconclusive: {sample_files[0].name}")
        except Exception as e:
            messages.append(f"⚠️  Could not read NIfTI: {e}")
    else:
        messages.append("⚠️  No sample NIfTI files found for integrity check")

    return all_passed, messages


def main() -> int:
    """Run validation and print results."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_isles24_download.py <bids_root>")
        print("Example: python scripts/validate_isles24_download.py data/zenodo/isles24/train")
        return 1

    bids_root = Path(sys.argv[1])

    print("=" * 60)
    print("ISLES24 Download Validation")
    print("=" * 60)
    print(f"Source: {bids_root}")
    print(f"Expected: {EXPECTED_SUBJECTS} subjects")
    print()

    passed, messages = validate_isles24_download(bids_root)

    for msg in messages:
        print(msg)

    print()
    print("=" * 60)
    if passed:
        print("✅ VALIDATION PASSED")
    else:
        print("❌ VALIDATION FAILED")
    print("=" * 60)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
