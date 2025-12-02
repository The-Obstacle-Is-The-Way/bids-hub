#!/usr/bin/env python3
"""
Validate ARC dataset download integrity.

This is a standalone wrapper around arc_bids.validation module.
Prefer using the CLI: `arc-bids validate data/openneuro/ds004884`

Usage:
    uv run python scripts/validate_download.py data/openneuro/ds004884
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from arc_bids.validation import validate_arc_download  # noqa: E402


def main() -> int:
    """Run validation and print results."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_download.py <bids_root>")
        print("Example: python scripts/validate_download.py data/openneuro/ds004884")
        print("")
        print("Prefer using the CLI: arc-bids validate data/openneuro/ds004884")
        return 1

    bids_root = Path(sys.argv[1])
    result = validate_arc_download(bids_root)

    print(result.summary())

    return 0 if result.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
