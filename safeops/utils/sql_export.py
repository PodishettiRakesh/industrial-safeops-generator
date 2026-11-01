"""
SQL export module.

This module exports generated data as SQL seed data with proper relationships.
"""

import pandas as pd
from typing import Dict
from pathlib import Path
from safeops.config import CSV_NULL_VALUE


def export_sql(data: Dict[str, pd.DataFrame], output_dir: Path):
    """
    Export all DataFrames as SQL INSERT statements.

    Args:
        data: Dictionary of DataFrames to export.
        output_dir: Output directory path.
    """
    # Define SQL type mappings for each table
    sql_types = {
        "plants": {
            "plant_id": "VARCHAR(20) PRIMARY KEY",
            "plant_name": "VARCHAR(100) NOT NULL",
            "location": "VARCHAR(100) NOT NULL",
            "created_at": "TIMESTAMP NOT NULL"
        },
        "machines": {
            "machine_id": "VARCHAR(20) PRIMARY KEY",
            "plant_id": "VARCHAR(20) NOT NULL",
            "machine_type": "VARCHAR(50) NOT NULL",
            "model_number": "VARCHAR(100) NOT NULL",
            "status": "VARCHAR(50) NOT NULL"
        },
        "safety_zones": {
            "zone_id": "VARCHAR(50) PRIMARY KEY",
            "machine_id": "VARCHAR(20) NOT NULL",
            "zone_type": "VARCHAR(50) NOT NULL",
            "risk_level": "VARCHAR(50) NOT NULL"
        },
        "interlocks": {
            "interlock_id": "VARCHAR(20) PRIMARY KEY",
            "machine_id": "VARCHAR(20) NOT NULL",
            "interlock_type": "VARCHAR(50) NOT NULL",
            "normal_state": "VARCHAR(50) NOT NULL"
        },
        "alarm_definitions": {
            "alarm_def_id": "VARCHAR(20) PRIMARY KEY",
            "machine_id": "VARCHAR(20) NOT NULL",
            "metric_name": "VARCHAR(50) NOT NULL",
            "severity": "VARCHAR(50) NOT NULL",
            "threshold_limit": "DECIMAL(10, 2) NOT NULL"
        },
        "operator_shifts": {
            "shift_id": "VARCHAR(50) PRIMARY KEY",
            "plant_id": "VARCHAR(20) NOT NULL",
            "operator_name": "VARCHAR(100) NOT NULL",
            "start_time": "TIMESTAMP NOT NULL",
            "end_time": "TIMESTAMP NOT NULL"
        },
        "machine_state_events": {
            "state_event_id": "INTEGER PRIMARY KEY",
            "machine_id": "VARCHAR(20) NOT NULL",
            "timestamp": "TIMESTAMP NOT NULL",
            "previous_state": "VARCHAR(50) NOT NULL",
            "new_state": "VARCHAR(50) NOT NULL",
            "interlock_status": "VARCHAR(50) NOT NULL",
            "source_event_id": "VARCHAR(50)"
        },
        "alarm_events": {
            "alarm_event_id": "VARCHAR(50) PRIMARY KEY",
            "alarm_def_id": "VARCHAR(20) NOT NULL",
            "timestamp": "TIMESTAMP NOT NULL",
            "current_value": "DECIMAL(10, 2) NOT NULL",
            "interlock_status": "VARCHAR(50) NOT NULL",
            "source_event_id": "VARCHAR(50)",
            "replay_group_id": "VARCHAR(50)"
        },
        "acknowledgements": {
            "ack_id": "VARCHAR(50) PRIMARY KEY",
            "alarm_event_id": "VARCHAR(50) NOT NULL",
            "shift_id": "VARCHAR(50) NOT NULL",
            "acknowledged_at": "TIMESTAMP NOT NULL"
        },
        "incidents": {
            "incident_id": "VARCHAR(50) PRIMARY KEY",
            "machine_id": "VARCHAR(20) NOT NULL",
            "alarm_event_id": "VARCHAR(50)",
            "severity_level": "VARCHAR(50) NOT NULL",
            "logged_at": "TIMESTAMP NOT NULL",
            "issue_type": "VARCHAR(100) NOT NULL"
        },
        "corrective_actions": {
            "action_id": "VARCHAR(50) PRIMARY KEY",
            "incident_id": "VARCHAR(50) NOT NULL",
            "action_taken": "VARCHAR(200) NOT NULL",
            "status": "VARCHAR(50) NOT NULL",
            "verified_at": "TIMESTAMP"
        }
    }

    # Export order: master data first, then event data
    export_order = [
        "plants",
        "machines",
        "safety_zones",
        "interlocks",
        "alarm_definitions",
        "operator_shifts",
        "machine_state_events",
        "alarm_events",
        "acknowledgements",
        "incidents",
        "corrective_actions"
    ]

    sql_file = output_dir / "seed_data.sql"

    with open(sql_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write("-- SafeOps Generator SQL Seed Data\n")
        f.write("-- Generated automatically from CSV export\n")
        f.write("-- Use with PostgreSQL, MySQL, or similar SQL databases\n\n")

        # Write CREATE TABLE statements with foreign keys
        f.write("-- ============================================\n")
        f.write("-- CREATE TABLE STATEMENTS\n")
        f.write("-- ============================================\n\n")

        # Plants (no foreign keys)
        f.write("CREATE TABLE plants (\n")
        f.write("    plant_id VARCHAR(20) PRIMARY KEY,\n")
        f.write("    plant_name VARCHAR(100) NOT NULL,\n")
        f.write("    location VARCHAR(100) NOT NULL,\n")
        f.write("    created_at TIMESTAMP NOT NULL\n")
        f.write(");\n\n")

        # Machines (FK to plants)
        f.write("CREATE TABLE machines (\n")
        f.write("    machine_id VARCHAR(20) PRIMARY KEY,\n")
        f.write("    plant_id VARCHAR(20) NOT NULL,\n")
        f.write("    machine_type VARCHAR(50) NOT NULL,\n")
        f.write("    model_number VARCHAR(100) NOT NULL,\n")
        f.write("    status VARCHAR(50) NOT NULL,\n")
        f.write("    FOREIGN KEY (plant_id) REFERENCES plants(plant_id)\n")
        f.write(");\n\n")

        # Safety Zones (FK to machines)
        f.write("CREATE TABLE safety_zones (\n")
        f.write("    zone_id VARCHAR(50) PRIMARY KEY,\n")
        f.write("    machine_id VARCHAR(20) NOT NULL,\n")
        f.write("    zone_type VARCHAR(50) NOT NULL,\n")
        f.write("    risk_level VARCHAR(50) NOT NULL,\n")
        f.write("    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)\n")
        f.write(");\n\n")

        # Interlocks (FK to machines)
        f.write("CREATE TABLE interlocks (\n")
        f.write("    interlock_id VARCHAR(20) PRIMARY KEY,\n")
        f.write("    machine_id VARCHAR(20) NOT NULL,\n")
        f.write("    interlock_type VARCHAR(50) NOT NULL,\n")
        f.write("    normal_state VARCHAR(50) NOT NULL,\n")
        f.write("    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)\n")
        f.write(");\n\n")

        # Alarm Definitions (FK to machines)
        f.write("CREATE TABLE alarm_definitions (\n")
        f.write("    alarm_def_id VARCHAR(20) PRIMARY KEY,\n")
        f.write("    machine_id VARCHAR(20) NOT NULL,\n")
        f.write("    metric_name VARCHAR(50) NOT NULL,\n")
        f.write("    severity VARCHAR(50) NOT NULL,\n")
        f.write("    threshold_limit DECIMAL(10, 2) NOT NULL,\n")
        f.write("    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)\n")
        f.write(");\n\n")

        # Operator Shifts (FK to plants)
        f.write("CREATE TABLE operator_shifts (\n")
        f.write("    shift_id VARCHAR(50) PRIMARY KEY,\n")
        f.write("    plant_id VARCHAR(20) NOT NULL,\n")
        f.write("    operator_name VARCHAR(100) NOT NULL,\n")
        f.write("    start_time TIMESTAMP NOT NULL,\n")
        f.write("    end_time TIMESTAMP NOT NULL,\n")
        f.write("    FOREIGN KEY (plant_id) REFERENCES plants(plant_id)\n")
        f.write(");\n\n")

        # Machine State Events (FK to machines)
        f.write("CREATE TABLE machine_state_events (\n")
        f.write("    state_event_id INTEGER PRIMARY KEY,\n")
        f.write("    machine_id VARCHAR(20) NOT NULL,\n")
        f.write("    timestamp TIMESTAMP NOT NULL,\n")
        f.write("    previous_state VARCHAR(50) NOT NULL,\n")
        f.write("    new_state VARCHAR(50) NOT NULL,\n")
        f.write("    interlock_status VARCHAR(50) NOT NULL,\n")
        f.write("    source_event_id VARCHAR(50),\n")
        f.write("    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)\n")
        f.write(");\n\n")

        # Alarm Events (FK to alarm_definitions)
        f.write("CREATE TABLE alarm_events (\n")
        f.write("    alarm_event_id VARCHAR(50) PRIMARY KEY,\n")
        f.write("    alarm_def_id VARCHAR(20) NOT NULL,\n")
        f.write("    timestamp TIMESTAMP NOT NULL,\n")
        f.write("    current_value DECIMAL(10, 2) NOT NULL,\n")
        f.write("    interlock_status VARCHAR(50) NOT NULL,\n")
        f.write("    source_event_id VARCHAR(50),\n")
        f.write("    replay_group_id VARCHAR(50),\n")
        f.write("    FOREIGN KEY (alarm_def_id) REFERENCES alarm_definitions(alarm_def_id)\n")
        f.write(");\n\n")

        # Acknowledgements (FK to alarm_events and operator_shifts)
        f.write("CREATE TABLE acknowledgements (\n")
        f.write("    ack_id VARCHAR(50) PRIMARY KEY,\n")
        f.write("    alarm_event_id VARCHAR(50) NOT NULL,\n")
        f.write("    shift_id VARCHAR(50) NOT NULL,\n")
        f.write("    acknowledged_at TIMESTAMP NOT NULL,\n")
        f.write("    FOREIGN KEY (alarm_event_id) REFERENCES alarm_events(alarm_event_id),\n")
        f.write("    FOREIGN KEY (shift_id) REFERENCES operator_shifts(shift_id)\n")
        f.write(");\n\n")

        # Incidents (FK to machines and alarm_events)
        f.write("CREATE TABLE incidents (\n")
        f.write("    incident_id VARCHAR(50) PRIMARY KEY,\n")
        f.write("    machine_id VARCHAR(20) NOT NULL,\n")
        f.write("    alarm_event_id VARCHAR(50),\n")
        f.write("    severity_level VARCHAR(50) NOT NULL,\n")
        f.write("    logged_at TIMESTAMP NOT NULL,\n")
        f.write("    issue_type VARCHAR(100) NOT NULL,\n")
        f.write("    FOREIGN KEY (machine_id) REFERENCES machines(machine_id),\n")
        f.write("    FOREIGN KEY (alarm_event_id) REFERENCES alarm_events(alarm_event_id)\n")
        f.write(");\n\n")

        # Corrective Actions (FK to incidents)
        f.write("CREATE TABLE corrective_actions (\n")
        f.write("    action_id VARCHAR(50) PRIMARY KEY,\n")
        f.write("    incident_id VARCHAR(50) NOT NULL,\n")
        f.write("    action_taken VARCHAR(200) NOT NULL,\n")
        f.write("    status VARCHAR(50) NOT NULL,\n")
        f.write("    verified_at TIMESTAMP,\n")
        f.write("    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)\n")
        f.write(");\n\n")

        # Write INSERT statements
        f.write("-- ============================================\n")
        f.write("-- INSERT STATEMENTS\n")
        f.write("-- ============================================\n\n")

        for table_name in export_order:
            if table_name not in data:
                continue

            df = data[table_name]
            if len(df) == 0:
                continue

            f.write(f"-- {table_name}\n")
            f.write(f"INSERT INTO {table_name} (")

            # Write column names
            columns = df.columns.tolist()
            f.write(", ".join(columns))
            f.write(") VALUES\n")

            # Write rows
            for i, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append("NULL")
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        values.append(f"'{val}'")

                f.write(f"    ({', '.join(values)})")
                if i < len(df) - 1:
                    f.write(",\n")
                else:
                    f.write(";\n\n")

        f.write("-- End of seed data\n")
