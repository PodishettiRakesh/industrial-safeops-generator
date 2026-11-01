"""
Generator and CLI tests for Phase 6.

Tests verify:
- End-to-end DEV generation
- Exact final DEV alarm-event count of 500
- All required CSV files are generated
- No accidental index columns
- Manifest counts match actual CSV rows
- Checksums match exported file bytes
- Validation report correctly reflects final data
- Repeated runs produce identical output bytes
- Reproducibility verification succeeds
- Invalid CLI arguments fail appropriately
"""

import numpy as np
import pandas as pd
import pytest
import json
import hashlib
import shutil
from pathlib import Path
import tempfile
from safeops.generator import generate_pipeline, verify_reproducibility
from safeops.config import init_rng, PROFILES


class TestGeneratorPipeline:
    """Test end-to-end generation pipeline."""

    def test_dev_generation_creates_output(self):
        """Verify DEV generation creates output directory and files."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            assert output_dir.exists()
            assert (output_dir / "plants.csv").exists()
            assert (output_dir / "machines.csv").exists()
            assert (output_dir / "ground_truth.csv").exists()
            assert (output_dir / "manifest.json").exists()

    def test_dev_alarm_event_count_exact(self):
        """Verify DEV profile generates exactly 500 alarm events."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            alarm_events = pd.read_csv(output_dir / "alarm_events.csv")
            assert len(alarm_events) == 500

    def test_all_csv_files_generated(self):
        """Verify all required CSV files are generated."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            required_files = [
                "plants.csv", "machines.csv", "safety_zones.csv", "interlocks.csv",
                "alarm_definitions.csv", "operator_shifts.csv", "machine_state_events.csv",
                "alarm_events.csv", "acknowledgements.csv", "incidents.csv",
                "corrective_actions.csv", "ground_truth.csv"
            ]

            for filename in required_files:
                assert (output_dir / filename).exists(), f"Missing file: {filename}"

    def test_no_index_columns_in_csv(self):
        """Verify CSV files don't have pandas index columns."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            # Read a CSV and check first column
            plants = pd.read_csv(output_dir / "plants.csv")
            assert plants.columns[0] == "plant_id"


class TestManifest:
    """Test manifest generation."""

    def test_manifest_created(self):
        """Verify manifest.json is created."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            assert (output_dir / "manifest.json").exists()

    def test_manifest_counts_match_csv_rows(self):
        """Verify manifest row counts match actual CSV rows."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            manifest = json.loads((output_dir / "manifest.json").read_text())

            for table, count in manifest["actual_row_counts"].items():
                if table == "ground_truth":
                    csv_file = output_dir / "ground_truth.csv"
                else:
                    csv_file = output_dir / f"{table}.csv"

                if csv_file.exists():
                    df = pd.read_csv(csv_file)
                    assert len(df) == count, f"Row count mismatch for {table}"

    def test_checksums_match_file_bytes(self):
        """Verify manifest checksums match actual file bytes."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            manifest = json.loads((output_dir / "manifest.json").read_text())

            for file_info in manifest["files"]:
                filepath = output_dir / file_info["name"]
                actual_checksum = hashlib.sha256(filepath.read_bytes()).hexdigest()
                assert actual_checksum == file_info["sha256"], f"Checksum mismatch for {file_info['name']}"


class TestReproducibility:
    """Test reproducibility."""

    def test_repeated_runs_identical(self):
        """Verify repeated runs produce identical output bytes."""
        rng1 = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir1:
            output_dir1 = Path(temp_dir1) / "output"
            generate_pipeline("dev", 20261022, output_dir1, rng1)
            manifest1 = json.loads((output_dir1 / "manifest.json").read_text())

        rng2 = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir2:
            output_dir2 = Path(temp_dir2) / "output"
            generate_pipeline("dev", 20261022, output_dir2, rng2)
            manifest2 = json.loads((output_dir2 / "manifest.json").read_text())

        assert manifest1 == manifest2

    def test_reproducibility_verification(self):
        """Verify reproducibility verification function works."""
        success = verify_reproducibility("dev", 20261022)
        assert success


class TestCLI:
    """Test CLI arguments (integration test with subprocess not required)."""

    def test_invalid_profile_fails(self):
        """Verify invalid profile argument is rejected."""
        import subprocess
        result = subprocess.run(
            ["python", "safeops/generator.py", "--profile", "invalid"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0


class TestValidationReport:
    """Test validation report in pipeline."""

    def test_validation_report_exported(self):
        """Verify validation_report.json is exported."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            assert (output_dir / "validation_report.json").exists()

    def test_validation_report_reflects_data(self):
        """Verify validation report correctly reflects final data."""
        rng = init_rng()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            generate_pipeline("dev", 20261022, output_dir, rng)

            report = json.loads((output_dir / "validation_report.json").read_text())

            assert report["profile"] == "dev"
            assert report["structural_integrity"] == "pass"
            assert "expected_anomalies" in report
            assert "detected_anomalies" in report
