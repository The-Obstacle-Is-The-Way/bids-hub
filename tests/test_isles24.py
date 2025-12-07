"""
Tests for ISLES'24 (Ischemic Stroke Lesion Segmentation 2024) dataset module.

These tests use synthetic BIDS structures to verify the ISLES'24 file-table builder
and flattened schema handling.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import nibabel as nib
import numpy as np
import pandas as pd
import pytest
from datasets import Features, Nifti, Sequence

from arc_bids.core import DatasetBuilderConfig
from arc_bids.isles24 import (
    build_and_push_isles24,
    build_isles24_file_table,
    get_isles24_features,
)


def _create_minimal_nifti(path: Path) -> None:
    """Create a minimal valid NIfTI file at the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.ones((2, 2, 2), dtype=np.float32)
    img = nib.Nifti1Image(data, np.eye(4))
    nib.save(img, path)


@pytest.fixture
def synthetic_isles24_root() -> Generator[Path, None, None]:
    """Create a synthetic ISLES'24 dataset for testing.

    Structure:
        isles24_train/
        ── participants.tsv
        ── rawdata/
        ── ─ sub-stroke0001/
        ── ─ ─ ses-01/ (Acute)
        ── ─ ─ ─ ct/  -> *_ncct.nii.gz
        ── ─ ─ ─ cta/ -> *_cta.nii.gz
        ── ─ ─ ─ ctp/ -> *_ctp.nii.gz
        ── ─ ─ ses-02/ (Follow-up)
        ── ─ ─ ─ dwi/ -> *_dwi.nii.gz, *_adc.nii.gz
        ── ─ sub-stroke0002/
        ── ─ ─ ... (partial data)
        ── derivatives/
        ── ─ perfusion_maps/
        ── ─ ─ sub-stroke0001/ses-01/perf/ -> *_Tmax, *_MTT, *_CBF, *_CBV
        ── ─ lesion_masks/
        ── ─ ─ sub-stroke0001/ses-02/anat/ -> *_msk.nii.gz
        ── ─ lvo_masks/
        ── ─ ─ sub-stroke0001/ses-01/anat/ -> *_msk.nii.gz
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "isles24_train"
        root.mkdir()
        rawdata = root / "rawdata"
        derivatives = root / "derivatives"

        # Create participants.tsv
        participants = pd.DataFrame(
            {
                "participant_id": ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"],
                "age": [65.0, 72.5, 55.0],
                "sex": ["M", "F", "F"],
                "nihss_admission": [12.0, 8.0, 15.0],
                "mrs_3months": [2.0, 1.0, 4.0],
                "thrombolysis": ["Yes", "No", "Yes"],
                "thrombectomy": ["No", "Yes", "No"],
            }
        )
        participants.to_csv(root / "participants.tsv", sep="\t", index=False)

        # --- Subject 1: Full Data ---
        s1 = "sub-stroke0001"

        # Raw ses-01
        _create_minimal_nifti(rawdata / s1 / "ses-01/ct" / f"{s1}_ses-01_ncct.nii.gz")
        _create_minimal_nifti(rawdata / s1 / "ses-01/cta" / f"{s1}_ses-01_cta.nii.gz")
        _create_minimal_nifti(rawdata / s1 / "ses-01/ctp" / f"{s1}_ses-01_ctp.nii.gz")

        # Raw ses-02
        _create_minimal_nifti(rawdata / s1 / "ses-02/dwi" / f"{s1}_ses-02_dwi.nii.gz")
        _create_minimal_nifti(rawdata / s1 / "ses-02/dwi" / f"{s1}_ses-02_adc.nii.gz")

        # Derivatives ses-01 (Perfusion)
        perf_dir = derivatives / "perfusion_maps" / s1 / "ses-01" / "perf"
        _create_minimal_nifti(perf_dir / f"{s1}_ses-01_Tmax.nii.gz")
        _create_minimal_nifti(perf_dir / f"{s1}_ses-01_MTT.nii.gz")
        _create_minimal_nifti(perf_dir / f"{s1}_ses-01_CBF.nii.gz")
        _create_minimal_nifti(perf_dir / f"{s1}_ses-01_CBV.nii.gz")

        # Derivatives ses-01 (Masks)
        lvo_path = derivatives / "lvo_masks" / s1 / "ses-01/anat" / f"{s1}_ses-01_msk.nii.gz"
        _create_minimal_nifti(lvo_path)
        cow_path = derivatives / "cow_segmentations" / s1 / "ses-01/anat"
        _create_minimal_nifti(cow_path / f"{s1}_ses-01_msk.nii.gz")

        # Derivatives ses-02 (Lesion)
        lesion_path = derivatives / "lesion_masks" / s1 / "ses-02/anat"
        _create_minimal_nifti(lesion_path / f"{s1}_ses-02_msk.nii.gz")

        # --- Subject 2: Partial Data (Missing CTP and LVO) ---
        s2 = "sub-stroke0002"
        _create_minimal_nifti(rawdata / s2 / "ses-01/ct" / f"{s2}_ses-01_ncct.nii.gz")
        _create_minimal_nifti(rawdata / s2 / "ses-01/cta" / f"{s2}_ses-01_cta.nii.gz")
        # Missing CTP
        # Missing Perfusion Maps

        _create_minimal_nifti(rawdata / s2 / "ses-02/dwi" / f"{s2}_ses-02_dwi.nii.gz")
        _create_minimal_nifti(rawdata / s2 / "ses-02/dwi" / f"{s2}_ses-02_adc.nii.gz")
        lesion_path_s2 = derivatives / "lesion_masks" / s2 / "ses-02/anat"
        _create_minimal_nifti(lesion_path_s2 / f"{s2}_ses-02_msk.nii.gz")

        # --- Subject 3: No Imaging Data (Only in Participants) ---
        # Should be excluded

        yield root


class TestBuildISLES24FileTable:
    """Tests for build_isles24_file_table function."""

    def test_build_returns_dataframe(self, synthetic_isles24_root: Path) -> None:
        """Test that it returns a pandas DataFrame."""
        df = build_isles24_file_table(synthetic_isles24_root)
        assert isinstance(df, pd.DataFrame)

    def test_correct_columns(self, synthetic_isles24_root: Path) -> None:
        """Test that all required columns are present."""
        df = build_isles24_file_table(synthetic_isles24_root)
        expected_cols = {
            "subject_id",
            "ncct",
            "cta",
            "ctp",
            "tmax",
            "mtt",
            "cbf",
            "cbv",
            "dwi",
            "adc",
            "lesion_mask",
            "lvo_mask",
            "cow_segmentation",
            "age",
            "sex",
            "nihss_admission",
            "mrs_3month",
            "thrombolysis",
            "thrombectomy",
        }
        assert set(df.columns) == expected_cols

    def test_flattens_sessions(self, synthetic_isles24_root: Path) -> None:
        """Test that ses-01 (Acute) and ses-02 (Follow-up) are in ONE row."""
        df = build_isles24_file_table(synthetic_isles24_root)
        s1 = df[df["subject_id"] == "sub-stroke0001"].iloc[0]

        # Ses-01 data
        assert s1["ncct"] is not None
        assert s1["cta"] is not None

        # Ses-02 data
        assert s1["dwi"] is not None
        assert s1["lesion_mask"] is not None

        # Confirm they are in the same row
        assert "sub-stroke0001" in s1["ncct"]
        assert "sub-stroke0001" in s1["lesion_mask"]

    def test_full_subject_has_all_paths(self, synthetic_isles24_root: Path) -> None:
        """Test that a subject with all files has no None values."""
        df = build_isles24_file_table(synthetic_isles24_root)
        s1 = df[df["subject_id"] == "sub-stroke0001"].iloc[0]

        for col in ["ncct", "cta", "ctp", "tmax", "dwi", "adc", "lesion_mask", "lvo_mask"]:
            assert s1[col] is not None
            assert Path(s1[col]).exists()

    def test_partial_subject_has_nones(self, synthetic_isles24_root: Path) -> None:
        """Test that missing optional files result in None."""
        df = build_isles24_file_table(synthetic_isles24_root)
        s2 = df[df["subject_id"] == "sub-stroke0002"].iloc[0]

        assert s2["ncct"] is not None
        assert s2["ctp"] is None  # Missing
        assert s2["tmax"] is None  # Missing
        assert s2["lvo_mask"] is None  # Missing

    def test_missing_rawdata_raises(self, tmp_path: Path) -> None:
        """Test that missing rawdata directory raises ValueError."""
        with pytest.raises(ValueError, match="rawdata directory not found"):
            build_isles24_file_table(tmp_path)

    def test_excludes_empty_subjects(self, synthetic_isles24_root: Path) -> None:
        """Test that subjects with no imaging data are excluded."""
        df = build_isles24_file_table(synthetic_isles24_root)
        # sub-stroke0003 has no data folders
        assert "sub-stroke0003" not in df["subject_id"].values


class TestGetISLES24Features:
    """Tests for get_isles24_features function."""

    def test_returns_features(self) -> None:
        """Test that get_isles24_features returns a Features object."""
        assert isinstance(get_isles24_features(), Features)

    def test_no_sequences(self) -> None:
        """Test that we are NOT using Sequence(Nifti) to avoid bugs."""
        features = get_isles24_features()

        # Check image columns are simple Nifti(), not Sequence(Nifti())
        for col in ["ncct", "dwi", "lesion_mask", "tmax"]:
            assert isinstance(features[col], Nifti)
            assert not isinstance(features[col], Sequence)


class TestBuildAndPushISLES24:
    """Tests for build_and_push_isles24 integration."""

    def test_dry_run_logic(self, synthetic_isles24_root: Path) -> None:
        """Test that dry run builds but does not push."""
        config = DatasetBuilderConfig(
            bids_root=synthetic_isles24_root,
            hf_repo_id="test/repo",
            dry_run=True,
        )

        with patch("arc_bids.isles24.build_hf_dataset") as mock_build:
            mock_build.return_value = MagicMock()
            build_and_push_isles24(config)
            mock_build.assert_called_once()
