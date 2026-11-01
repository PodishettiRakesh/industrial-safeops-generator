"""
Main generator module with CLI orchestration.

This module provides the command-line interface and orchestrates
the full data generation pipeline.
"""

import argparse
import json
import hashlib
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict
import pandas as pd
import numpy as np
import sys

from safeops.config import (
    init_rng,
    get_profile,
    SEED,
    SIMULATION_START_UTC,
    SIMULATION_DAYS,
    TIMESTAMP_FORMAT,
    CSV_ENCODING,
    CSV_NULL_VALUE,
    FLOAT_FORMAT,
    PROFILES
)
from safeops.utils.master_gen import generate_master_data
from safeops.utils.event_engine import generate_events
from safeops.utils.anomaly_injector import inject_anomalies
from safeops.utils.sql_export import export_sql
from safeops.validate import validate


def main():
    """
    Main entry point for the SafeOps Generator CLI.

    Parses command-line arguments and orchestrates the generation pipeline.
    """
    parser = argparse.ArgumentParser(description="SafeOps Generator - Synthetic Industrial Operations Data")
    parser.add_argument("--profile", choices=["dev", "full"], required=True,
                        help="Generation profile")
    parser.add_argument("--output-dir", default="output",
                        help="Output directory for generated files")
    parser.add_argument("--seed", type=int, default=SEED,
                        help=f"Random seed for reproducibility (default: {SEED})")
    parser.add_argument("--verify-reproducibility", action="store_true",
                        help="Run reproducibility verification")

    args = parser.parse_args()

    # Validate seed
    if args.seed != SEED:
        print(f"Warning: Using non-default seed {args.seed}. Reproducibility comparisons require the same seed.")

    # Initialize RNG
    rng = init_rng(args.seed)

    # Create output directory
    output_dir = Path(args.output_dir)

    if args.verify_reproducibility:
        success = verify_reproducibility(args.profile, args.seed)
        sys.exit(0 if success else 1)

    # Run generation pipeline
    try:
        generate_pipeline(args.profile, args.seed, output_dir, rng)
        print(f"\nGeneration complete. Output written to: {output_dir.absolute()}")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


def generate_pipeline(profile: str, seed: int, output_dir: Path, rng: np.random.Generator):
    """
    Orchestrate the complete generation pipeline.

    Args:
        profile: Profile name ('dev' or 'full').
        seed: Random seed.
        output_dir: Output directory path.
        rng: Random number generator.
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting SafeOps Generator - Profile: {profile}, Seed: {seed}")

    # 1. Generate master data
    print("Generating master data...")
    master_data = generate_master_data(profile, rng)

    # 2. Generate event data
    print("Generating event data...")
    event_data = generate_events(master_data, profile, rng)

    # 3. Inject anomalies
    print("Injecting anomalies...")
    modified_event_data, ground_truth, anomaly_summary = inject_anomalies(
        master_data, event_data, profile, rng
    )

    # 4. Validate final data
    print("Validating final data...")
    all_data = {**master_data, **modified_event_data}
    validation_report = validate(all_data, ground_truth, profile)

    # Check for validation failures
    if validation_report["structural_integrity"] == "fail":
        print("\nERROR: Structural validation failed!", file=sys.stderr)
        print("Structural errors:", file=sys.stderr)
        for error in validation_report["structural_errors"]:
            print(f"  - {error}", file=sys.stderr)
        raise RuntimeError("Structural validation failed")

    # Check for unlabelled detections
    total_unlabelled = sum(
        r.get("unlabelled_detections", 0)
        for r in validation_report["ground_truth_reconciliation"].values()
    )
    if total_unlabelled > 0:
        print(f"\nWARNING: {total_unlabelled} unlabelled anomaly detections found")

    # 5. Export CSV files
    print("Exporting CSV files...")
    export_csvs(all_data, ground_truth, output_dir)

    # 5.5. Export SQL seed data
    print("Exporting SQL seed data...")
    export_sql(all_data, output_dir)

    # 6. Export validation report
    print("Exporting validation report...")
    validation_path = output_dir / "validation_report.json"
    with open(validation_path, 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2)

    # 7. Generate manifest
    print("Generating manifest...")
    manifest = generate_manifest(
        profile, seed, all_data, ground_truth, anomaly_summary, validation_report, output_dir
    )
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nExported {len(all_data) + 4} files to {output_dir.absolute()}")


def export_csvs(data: Dict[str, pd.DataFrame], ground_truth: pd.DataFrame, output_dir: Path):
    """
    Export all DataFrames to CSV files with deterministic formatting.

    Args:
        data: Dictionary of DataFrames to export.
        ground_truth: Ground truth DataFrame.
        output_dir: Output directory path.
    """
    # Column order for each table
    column_orders = {
        "plants": ["plant_id", "plant_name", "location", "created_at"],
        "machines": ["machine_id", "plant_id", "machine_type", "model_number", "status"],
        "safety_zones": ["zone_id", "machine_id", "zone_type", "risk_level"],
        "interlocks": ["interlock_id", "machine_id", "interlock_type", "normal_state"],
        "alarm_definitions": ["alarm_def_id", "machine_id", "metric_name", "severity", "threshold_limit"],
        "operator_shifts": ["shift_id", "plant_id", "operator_name", "start_time", "end_time"],
        "machine_state_events": ["state_event_id", "machine_id", "timestamp", "previous_state",
                              "new_state", "interlock_status", "source_event_id"],
        "alarm_events": ["alarm_event_id", "alarm_def_id", "timestamp", "current_value",
                        "interlock_status", "source_event_id", "replay_group_id"],
        "acknowledgements": ["ack_id", "alarm_event_id", "shift_id", "acknowledged_at"],
        "incidents": ["incident_id", "machine_id", "alarm_event_id", "severity_level",
                    "logged_at", "issue_type"],
        "corrective_actions": ["action_id", "incident_id", "action_taken", "status", "verified_at"]
    }

    # Export each table
    for table_name, df in data.items():
        if table_name in column_orders:
            filepath = output_dir / f"{table_name}.csv"
            df[column_orders[table_name]].to_csv(
                filepath,
                index=False,
                encoding=CSV_ENCODING,
                date_format=TIMESTAMP_FORMAT,
                float_format=FLOAT_FORMAT,
                na_rep=CSV_NULL_VALUE,
                lineterminator="\n"
            )

    # Export ground truth
    ground_truth_path = output_dir / "ground_truth.csv"
    ground_truth.to_csv(
        ground_truth_path,
        index=False,
        encoding=CSV_ENCODING,
        na_rep=CSV_NULL_VALUE,
        lineterminator="\n"
    )


def generate_manifest(
    profile: str,
    seed: int,
    data: Dict[str, pd.DataFrame],
    ground_truth: pd.DataFrame,
    anomaly_summary: Dict,
    validation_report: Dict,
    output_dir: Path
) -> Dict:
    """
    Generate manifest with file metadata and checksums.

    Args:
        profile: Profile name.
        seed: Random seed.
        data: Dictionary of DataFrames.
        ground_truth: Ground truth DataFrame.
        anomaly_summary: Anomaly injection summary.
        validation_report: Validation report.
        output_dir: Output directory.

    Returns:
        Manifest dictionary.
    """
    import sys
    import pandas as pd

    # Calculate simulation end
    from datetime import timedelta
    sim_start = datetime.fromisoformat(SIMULATION_START_UTC.replace("Z", "+00:00"))
    sim_end = sim_start + timedelta(days=SIMULATION_DAYS)

    # Row counts
    row_counts = {
        table: len(df) for table, df in data.items()
    }
    row_counts["ground_truth"] = len(ground_truth)

    # File info and checksums
    files = []
    # Include CSV, JSON, and SQL files, but exclude manifest.json itself
    csv_files = list(output_dir.glob("*.csv")) + list(output_dir.glob("*.json")) + list(output_dir.glob("*.sql"))

    for filepath in csv_files:
        # Skip manifest.json to avoid self-referential checksum
        if filepath.name == "manifest.json":
            continue
        file_bytes = filepath.read_bytes()
        checksum = hashlib.sha256(file_bytes).hexdigest()
        files.append({
            "name": filepath.name,
            "size": len(file_bytes),
            "sha256": checksum
        })

    # Get dependency versions
    dependency_versions = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pandas": pd.__version__,
        "numpy": np.__version__
    }

    manifest = {
        "seed": seed,
        "profile": profile,
        "simulation_start": SIMULATION_START_UTC,
        "simulation_end": sim_end.strftime(TIMESTAMP_FORMAT),
        "expected_row_counts": {
            "plants": PROFILES[profile]["num_plants"],
            "machines": PROFILES[profile]["num_machines"],
            "alarm_definitions": PROFILES[profile]["num_alarm_definitions"],
            "alarm_events": PROFILES[profile]["num_alarm_events"]
        },
        "actual_row_counts": row_counts,
        "anomaly_counts": anomaly_summary,
        "validation_status": validation_report["overall_status"],
        "generator_version": "1.0.0",
        "python_version": dependency_versions["python"],
        "dependency_versions": dependency_versions,
        "files": files
    }

    return manifest


def verify_reproducibility(profile: str, seed: int) -> bool:
    """
    Verify reproducibility by generating the same profile twice in separate temp directories.

    Args:
        profile: Profile name.
        seed: Random seed.

    Returns:
        True if reproducible, False otherwise.
    """
    print(f"Verifying reproducibility for profile: {profile}, seed: {seed}")

    # Create two temporary directories
    temp_dir1 = Path(tempfile.mkdtemp(prefix="safeops_verify1_"))
    temp_dir2 = Path(tempfile.mkdtemp(prefix="safeops_verify2_"))

    try:
        # Generate in first directory
        print(f"  Generating in {temp_dir1}...")
        rng1 = init_rng(seed)
        generate_pipeline(profile, seed, temp_dir1, rng1)

        # Generate in second directory
        print(f"  Generating in {temp_dir2}...")
        rng2 = init_rng(seed)
        generate_pipeline(profile, seed, temp_dir2, rng2)

        # Compare files
        print("  Comparing files...")
        files1 = sorted(temp_dir1.glob("*"))
        files2 = sorted(temp_dir2.glob("*"))

        if len(files1) != len(files2):
            print(f"  ERROR: File count mismatch ({len(files1)} vs {len(files2)})")
            return False

        all_match = True
        for f1, f2 in zip(files1, files2):
            if f1.name != f2.name:
                print(f"  ERROR: Filename mismatch ({f1.name} vs {f2.name})")
                all_match = False
                continue

            bytes1 = f1.read_bytes()
            bytes2 = f2.read_bytes()

            if bytes1 != bytes2:
                print(f"  ERROR: File content mismatch: {f1.name}")
                all_match = False
            else:
                print(f"  OK {f1.name}")

        if all_match:
            print("\n[OK] Reproducibility verification PASSED")
            return True
        else:
            print("\n[FAIL] Reproducibility verification FAILED")
            return False

    finally:
        # Clean up temporary directories
        shutil.rmtree(temp_dir1, ignore_errors=True)
        shutil.rmtree(temp_dir2, ignore_errors=True)


if __name__ == "__main__":
    main()
