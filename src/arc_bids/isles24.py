"""
ISLES'24 (Ischemic Stroke Lesion Segmentation 2024) dataset module.

This module converts the ISLES'24 BIDS dataset (Zenodo record 17652035) into a
Hugging Face Dataset.

Dataset info:
- Source: Zenodo (https://zenodo.org/records/17652035)
- Description: Multimodal acute stroke (CT/CTA/CTP) + follow-up (DWI/ADC)
- License: CC BY-NC-SA 4.0
- Task: Acute stroke lesion segmentation & outcome prediction

Schema Design:
- One row per SUBJECT (flattened).
- Acute admission (ses-01) and Follow-up (ses-02) are in the same row.
- This aligns with the ML task: Input (Acute) -> Target (Follow-up Lesion).
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Features, Nifti, Value

from .core import DatasetBuilderConfig, build_hf_dataset, push_dataset_to_hub

logger = logging.getLogger(__name__)


def _get_participant_value(
    row: "pd.Series[Any]",
    col: str,
    type_func: Callable[[Any], Any],
) -> Any:
    """Safely extract and convert a value from a participant row."""
    val = row.get(col)
    if pd.isna(val):
        return None
    try:
        return type_func(val)
    except (ValueError, TypeError):
        return None


def _find_single_nifti(search_dir: Path, pattern: str, required: bool = False) -> str | None:
    """
    Find a single NIfTI file matching a pattern in a directory.

    Args:
        search_dir: Directory to search (e.g., sub-01/ses-01/ct).
        pattern: Glob pattern (e.g., "*_ncct.nii.gz").
        required: If True, log a warning if not found.

    Returns:
        Absolute path to the file, or None if not found.
    """
    if not search_dir.exists():
        if required:
            logger.debug("Missing directory: %s", search_dir)
        return None

    matches = list(search_dir.rglob(pattern))
    if not matches:
        if required:
            logger.debug("No file matching %s in %s", pattern, search_dir)
        return None

    # Sort to ensure determinism if multiple (though shouldn't happen for single modalities)
    matches.sort(key=lambda p: p.name)
    return str(matches[0].resolve())


def build_isles24_file_table(bids_root: Path) -> pd.DataFrame:
    """
    Build a file table for the ISLES'24 dataset.

    Walks the directory structure and builds a pandas DataFrame with
    one row per SUBJECT (flattening ses-01 and ses-02).

    Structure:
    - rawdata/sub-X/ses-01/ (Acute): ct, cta, ctp
    - rawdata/sub-X/ses-02/ (Follow-up): dwi
    - derivatives/perfusion_maps/sub-X/ses-01/ (perf): tmax, mtt, cbf, cbv
    - derivatives/lesion_masks/sub-X/ses-02/ (mask): lesion
    - derivatives/lvo_masks/sub-X/ses-01/ (mask): lvo (optional)
    - derivatives/cow_segmentations/sub-X/ses-01/ (mask): cow (optional)

    Args:
        bids_root: Path to the root of the ISLES24 dataset.

    Returns:
        DataFrame with one row per subject.
    """
    bids_root = Path(bids_root).resolve()
    rawdata_root = bids_root / "rawdata"
    derivatives_root = bids_root / "derivatives"

    if not rawdata_root.exists():
        raise ValueError(f"rawdata directory not found at {rawdata_root}")

    # Read participants.tsv
    participants_tsv = bids_root / "participants.tsv"
    if participants_tsv.exists():
        participants = pd.read_csv(participants_tsv, sep="\t")
        # Ensure subject_id matches directory names (sub-strokeXXXX)
        # BIDS spec says participant_id column should have "sub-" prefix
    else:
        logger.warning("participants.tsv not found. Clinical metadata will be missing.")
        participants = pd.DataFrame(columns=["participant_id"])

    rows = []

    # Iterate over subjects in rawdata
    subject_dirs = sorted(rawdata_root.glob("sub-*"))
    for subject_dir in subject_dirs:
        subject_id = subject_dir.name  # e.g., "sub-stroke0001"

        # --- SESSION 01: ACUTE (CT/CTA/CTP) ---
        ses01_dir = subject_dir / "ses-01"

        # Raw CTs
        ncct = _find_single_nifti(ses01_dir / "ct", "*_ncct.nii.gz")
        cta = _find_single_nifti(ses01_dir / "cta", "*_cta.nii.gz")
        ctp = _find_single_nifti(ses01_dir / "ctp", "*_ctp.nii.gz")

        # Perfusion Maps (Derivatives - ses-01)
        # Path: derivatives/perfusion_maps/sub-X/ses-01/perf/
        perf_dir = derivatives_root / "perfusion_maps" / subject_id / "ses-01" / "perf"
        tmax = _find_single_nifti(perf_dir, "*_Tmax.nii.gz")
        mtt = _find_single_nifti(perf_dir, "*_MTT.nii.gz")
        cbf = _find_single_nifti(perf_dir, "*_CBF.nii.gz")
        cbv = _find_single_nifti(perf_dir, "*_CBV.nii.gz")

        # --- SESSION 02: FOLLOW-UP (MRI) ---
        ses02_dir = subject_dir / "ses-02"

        # Raw MR
        # Note: DWI/ADC often in 'dwi' folder
        dwi = _find_single_nifti(ses02_dir / "dwi", "*_dwi.nii.gz")
        adc = _find_single_nifti(ses02_dir / "dwi", "*_adc.nii.gz")

        # --- DERIVATIVES (MASKS) ---

        # Lesion Mask (ses-02)
        # Path: derivatives/lesion_masks/sub-X/ses-02/anat/
        lesion_dir = derivatives_root / "lesion_masks" / subject_id / "ses-02" / "anat"
        lesion_mask = _find_single_nifti(lesion_dir, "*_msk.nii.gz")

        # LVO Mask (ses-01) - Optional
        lvo_dir = derivatives_root / "lvo_masks" / subject_id / "ses-01" / "anat"
        lvo_mask = _find_single_nifti(lvo_dir, "*_msk.nii.gz")

        # CoW Segmentation (ses-01) - Optional
        cow_dir = derivatives_root / "cow_segmentations" / subject_id / "ses-01" / "anat"
        cow_seg = _find_single_nifti(cow_dir, "*_msk.nii.gz")

        # --- METADATA ---
        # Get row from participants dataframe
        meta = {}
        if not participants.empty:
            subj_row = participants[participants["participant_id"] == subject_id]
            if not subj_row.empty:
                # Convert relevant columns
                # Column names based on ISLES24 participants.tsv
                row_data = subj_row.iloc[0]
                meta["age"] = _get_participant_value(row_data, "age", float)
                meta["sex"] = _get_participant_value(row_data, "sex", str)
                meta["nihss_admission"] = _get_participant_value(row_data, "nihss_admission", float)
                meta["mrs_3month"] = _get_participant_value(row_data, "mrs_3months", float)
                meta["thrombolysis"] = _get_participant_value(row_data, "thrombolysis", str)
                meta["thrombectomy"] = _get_participant_value(row_data, "thrombectomy", str)

        row = {
            "subject_id": subject_id,
            # Acute
            "ncct": ncct,
            "cta": cta,
            "ctp": ctp,
            "tmax": tmax,
            "mtt": mtt,
            "cbf": cbf,
            "cbv": cbv,
            # Follow-up
            "dwi": dwi,
            "adc": adc,
            # Masks
            "lesion_mask": lesion_mask,
            "lvo_mask": lvo_mask,
            "cow_segmentation": cow_seg,
            # Metadata (defaults to None if missing)
            "age": meta.get("age"),
            "sex": meta.get("sex"),
            "nihss_admission": meta.get("nihss_admission"),
            "mrs_3month": meta.get("mrs_3month"),
            "thrombolysis": meta.get("thrombolysis"),
            "thrombectomy": meta.get("thrombectomy"),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def get_isles24_features() -> Features:
    """
    Get the Flattened Schema for ISLES'24.
    """
    return Features(
        {
            "subject_id": Value("string"),
            # Acute (ses-01)
            "ncct": Nifti(),
            "cta": Nifti(),
            "ctp": Nifti(),
            # Perfusion Maps
            "tmax": Nifti(),
            "mtt": Nifti(),
            "cbf": Nifti(),
            "cbv": Nifti(),
            # Follow-up (ses-02)
            "dwi": Nifti(),
            "adc": Nifti(),
            # Derivatives
            "lesion_mask": Nifti(),
            "lvo_mask": Nifti(),
            "cow_segmentation": Nifti(),
            # Metadata
            "age": Value("float32"),
            "sex": Value("string"),
            "nihss_admission": Value("float32"),
            "mrs_3month": Value("float32"),
            "thrombolysis": Value("string"),
            "thrombectomy": Value("string"),
        }
    )


def build_and_push_isles24(config: DatasetBuilderConfig) -> None:
    """
    Orchestrate the ISLES'24 build and upload.
    """
    # 1. Build File Table
    logger.info("Building ISLES'24 file table from %s...", config.bids_root)
    file_table = build_isles24_file_table(config.bids_root)
    logger.info("Found %d subjects.", len(file_table))

    # 2. Get Features
    features = get_isles24_features()

    # 3. Build HF Dataset
    logger.info("Building HF Dataset object...")
    ds = build_hf_dataset(config, file_table, features)

    # 4. Push to Hub
    if not config.dry_run:
        # One shard per subject (149 total) to prevent OOM
        num_shards = len(file_table)
        logger.info("Pushing to %s with num_shards=%d...", config.hf_repo_id, num_shards)
        push_dataset_to_hub(ds, config, num_shards=num_shards)
    else:
        logger.info("Dry run complete. Dataset built but not pushed.")
