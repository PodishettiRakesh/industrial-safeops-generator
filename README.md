# SafeOps Generator

A deterministic synthetic data engine simulating 30 days of industrial OT telemetry, operator workflows, and critical safety violations for testing and validating safety monitoring systems.

## Project Purpose

The SafeOps Generator produces realistic, relationally consistent synthetic industrial factory operations data with explicitly injected and labeled safety anomalies. It is designed for testing safety monitoring, anomaly detection, and data validation systems in industrial operational technology (OT) environments.

## Business Context

Industrial factories generate complex time-series data from machines, safety systems, and operator workflows. Testing safety monitoring systems requires realistic datasets that include:
- Normal operational baselines
- Safety anomaly scenarios
- Relational consistency across entities
- Deterministic reproducibility for test comparisons

This generator provides such datasets with:
- Master/reference data (plants, machines, safety zones, interlocks, alarm definitions)
- Time-series event data (shifts, state changes, alarms, acknowledgements, incidents, corrective actions)
- Five labeled anomaly categories
- Ground-truth documentation for validation

## Prerequisites

- Python 3.11 or higher
- pandas 2.2.3
- numpy 2.1.3
- pytest 8.3.3 (for testing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/PodishettiRakesh/industrial-safeops-generator.git
cd industrial-safeops-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### DEV Profile (Fast Testing)

Generate a small dataset for development and testing:
```bash
python -m safeops.generator --profile dev --output-dir output_dev
```

**DEV Profile Specs:**
- 2 plants
- 5 machines
- 10 alarm definitions
- 500 alarm events
- ~400 acknowledgements
- ~250-1000 machine state events
- ~50-100 incidents
- ~100-300 corrective actions

### FULL Profile (Large-Scale Testing)

Generate a large-scale dataset:
```bash
python -m safeops.generator --profile full --output-dir output_full
```

**FULL Profile Specs:**
- 4 plants
- 60 machines
- 200 alarm definitions
- 50,000 alarm events
- ~40,000 acknowledgements
- ~3,000-12,000 machine state events
- ~50-100 incidents
- ~100-300 corrective actions

### CLI Options

```bash
python -m safeops.generator --profile {dev|full} [OPTIONS]

Options:
  --profile {dev,full}   Generation profile (required)
  --output-dir PATH      Output directory (default: output)
  --seed INT             Random seed for reproducibility (default: 20261022)
  --verify-reproducibility  Run reproducibility verification
```

### Reproducibility Verification

Verify that identical seeds produce identical outputs:
```bash
python -m safeops.generator --profile full --verify-reproducibility
```

This generates the dataset twice in temporary directories and compares all files byte-for-byte.

## Generation Pipeline

The generator follows this pipeline:

1. **Initialize RNG** - Seeded deterministic random number generation
2. **Generate Master Data** - Plants, machines, safety zones, interlocks, alarm definitions
3. **Generate Event Data** - Operator shifts, machine state events, alarm events, acknowledgements, incidents, corrective actions
4. **Inject Anomalies** - Five labeled anomaly categories
5. **Validate** - Structural integrity and business-rule validation
6. **Export CSVs** - All tables with deterministic formatting
7. **Export SQL** - Generate seed_data.sql with CREATE TABLE and INSERT statements
8. **Generate Manifest** - Checksums and metadata

## Data Schema

The generator produces 11 core data entities organized into master/reference data and time-series event data.

> **📖 For detailed field definitions, validation rules, and relationships, see [DATA_DICTIONARY.md](DATA_DICTIONARY.md)**

### Entity Overview

| Entity | Purpose | Key Relationships |
|--------|---------|------------------|
| **Plants** | Physical factory locations | → Machines (1:N) |
| **Machines** | Manufacturing equipment | ← Plants (N:1), → Safety Zones (1:N), → Interlocks (1:N), → Alarm Definitions (1:N) |
| **Safety Zones** | Protected areas around machines | ← Machines (N:1) |
| **Interlocks** | Safety protection mechanisms | ← Machines (N:1) |
| **Alarm Definitions** | Configured alarm thresholds | ← Machines (N:1), → Alarm Events (1:N) |
| **Operator Shifts** | Operator work periods | ← Plants (N:1), → Acknowledgements (1:N) |
| **Machine State Events** | Machine status transitions | ← Machines (N:1) |
| **Alarm Events** | Threshold breach occurrences | ← Alarm Definitions (N:1), → Acknowledgements (1:N), → Incidents (1:1 or 0:1) |
| **Acknowledgements** | Operator responses to alarms | ← Alarm Events (N:1), ← Operator Shifts (N:1) |
| **Incidents** | Safety incidents | ← Machines (N:1), ← Alarm Events (N:1 or 0:1), → Corrective Actions (1:N) |
| **Corrective Actions** | Remediation actions | ← Incidents (N:1) |

## Anomaly Categories

### Nuisance Alarm Clusters (Operational Metric)

**Description:** Groups of 5 or more Low/Medium severity alarms from the same machine within 10 minutes
**Detection Rule:** 5+ Low/Medium severity alarms from same machine in 10-minute window
**Business Significance:** Indicates repeated minor issues that may mask genuine safety problems
**Validation Report:** Includes cluster count, affected machines, and cluster details

### 1. ACK_BEFORE_ALARM
**Description:** Acknowledgement timestamp precedes alarm timestamp
**Injection Rule:** Select ~1% of acknowledgements and set acknowledged_at to 1 hour before alarm timestamp
**Detection:** acknowledgement_time < alarm_time
**Business Rule:** Acknowledgements must occur after alarms

### 2. IMPOSSIBLE_INTERLOCK
**Description:** Machine in Operational state with Bypassed interlock
**Injection Rule:** Select ~1% of Operational state events and set interlock_status to Bypassed
**Detection:** new_state == "Operational" AND interlock_status == "Bypassed"
**Business Rule:** Operational machines must have Secure interlock

### 3. MISSING_CONTEXT
**Description:** Incident missing alarm event reference
**Injection Rule:** Select ~1% of incidents and set alarm_event_id to null
**Detection:** alarm_event_id is null
**Business Rule:** Incidents should reference triggering alarm events

### 4. REPLAY_FLOOD
**Description:** Duplicate alarm events (replay attack simulation)
**Injection Rule:** Duplicate 50 contiguous alarm events with new IDs and replay_group_id
**Detection:** Replay records have replay_group_id
**Business Rule:** Each alarm event should be unique
**Note:** Fixed at 50 records (not percentage-based)

### 5. UNVERIFIED_CLOSURE
**Description:** Closed corrective action without verification timestamp
**Injection Rule:** Select ~1% of Closed actions and set verified_at to null
**Detection:** status == "Closed" AND verified_at is null
**Business Rule:** Closed actions must have verification timestamps

## Incident Traceability

Incidents can be traced to relevant machine-state history and corrective actions through foreign key relationships:

### Traceability Paths

1. **Incident → Machine State History**
   - Join: `incidents.machine_id = machine_state_events.machine_id`
   - Filter: `machine_state_events.timestamp <= incidents.logged_at`
   - Purpose: View machine state transitions leading up to the incident

2. **Incident → Triggering Alarm**
   - Join: `incidents.alarm_event_id = alarm_events.alarm_event_id`
   - Join: `alarm_events.alarm_def_id = alarm_definitions.alarm_def_id`
   - Purpose: Identify the alarm that triggered the incident

3. **Incident → Corrective Actions**
   - Join: `incidents.incident_id = corrective_actions.incident_id`
   - Purpose: View all remediation actions taken for the incident

### Example Query (Pseudo-SQL)

```sql
-- View incident with machine state history and corrective actions
SELECT
    i.incident_id,
    i.severity_level,
    i.logged_at,
    mse.previous_state,
    mse.new_state,
    mse.interlock_status,
    ca.action_taken,
    ca.status,
    ca.verified_at
FROM incidents i
LEFT JOIN machine_state_events mse
    ON i.machine_id = mse.machine_id
    AND mse.timestamp <= i.logged_at
LEFT JOIN corrective_actions ca
    ON i.incident_id = ca.incident_id
WHERE i.incident_id = 'INC-2026-000001'
ORDER BY mse.timestamp DESC, ca.action_id;
```

**Note:** For incidents with MISSING_CONTEXT anomaly (alarm_event_id is null), the triggering alarm cannot be traced.

## Ground Truth

The `ground_truth.csv` file documents all injected anomalies separately from the operational data.

**Columns:**
- target_table (string): Name of affected table
- entity_id (string): Primary key of affected record
- anomaly_type (string): One of the five anomaly categories
- description (string): Explanation of the violation

**Design Principles:**
- One label per affected record per anomaly category
- Stable deterministic ordering (by target_table, entity_id)
- No ground-truth labels embedded in operational tables
- Descriptions explain violations without exposing unnecessary data

## Validation

The generator performs structural and business-rule validation before export:

### Structural Integrity Checks
- Required tables and columns exist
- Primary keys are non-null and unique
- Foreign keys resolve to existing records
- Enum values are valid
- Timestamps are parseable
- Row counts match profile targets

### Business-Rule Validation
- Independent detection of all five anomaly categories
- Comparison with ground truth labels
- Reconciliation metrics (matched, missed, unlabelled)

### Validation Report

The `validation_report.json` file contains:
- Profile name
- Expected vs actual row counts
- Structural integrity status
- Structural errors (if any)
- Expected and detected anomaly counts
- Ground truth reconciliation metrics
- Nuisance alarm cluster metrics (cluster count, affected machines, cluster details)
- Incident traceability validation (incidents with machine state history, corrective actions, triggering alarms)
- Overall validation status

**Status Codes:**
- `pass`: All checks passed
- `fail`: Structural errors or critical issues found

## Reproducibility

The generator is fully deterministic when using the same seed:

- Same seed → identical data (byte-for-byte)
- Different seed → different random values, same structure
- Default seed: 20261022

**Verification:**
```bash
python -m safeops.generator --profile full --verify-reproducibility
```

This verifies that two independent generations produce identical files.

**Notes:**
- Reproducibility is guaranteed within the same environment
- Dependency versions are recorded in manifest.json
- Changes in dependency versions may affect output

## Output Files

Total: 15 files

### Operational CSVs (11 files)
- plants.csv
- machines.csv
- safety_zones.csv
- interlocks.csv
- alarm_definitions.csv
- operator_shifts.csv
- machine_state_events.csv
- alarm_events.csv
- acknowledgements.csv
- incidents.csv
- corrective_actions.csv

### Metadata Files (3 files)
- ground_truth.csv - Anomaly labels
- validation_report.json - Validation results
- manifest.json - File metadata and checksums

### SQL Export (1 file)
- seed_data.sql - SQL seed data with CREATE TABLE and INSERT statements

### CSV Format Specifications
- Encoding: UTF-8
- No pandas index columns
- Stable column order per table
- Timestamp format: %Y-%m-%dT%H:%M:%SZ
- Float format: %.6f
- Null representation: empty string
- Line endings: Unix (\n)

### Manifest Contents
- Seed and profile
- Simulation start and end timestamps
- Expected vs actual row counts
- Anomaly injection summary
- Validation status
- Generator version
- Python, pandas, NumPy versions
- File list with sizes and SHA-256 checksums (excludes manifest.json itself)

## Known Assumptions and Limitations

### Assumptions
- 8-hour shift duration
- Severity-based acknowledgement SLAs (Critical: 15min, Low: 2hrs)
- Interlock normal states by type
- Anomaly budget of ~1% per category (except REPLAY_FLOOD)
- Simulation window: 30 days starting 2026-01-01

### Limitations
- No external database integration (CSV and SQL export only, no direct database connection)
- No frontend or visualization
- No LLM or external data sources
- Replay flood fixed at 50 records (not configurable)
- Validation does not repair injected anomalies
- Reproducibility not guaranteed across different dependency versions
- SQL export uses generic SQL syntax

## Testing

Run the full test suite:
```bash
pytest -q
```

Run specific test modules:
```bash
pytest safeops/tests/test_config.py
pytest safeops/tests/test_master_data.py
pytest safeops/tests/test_event_engine.py
pytest safeops/tests/test_anomaly_injector.py
pytest safeops/tests/test_validate.py
pytest safeops/tests/test_generator.py
```

**Test Coverage:**
- Configuration: 58 tests
- Master data: 102 tests
- Event engine: 80 tests
- Anomaly injector: 56 tests
- Validation: 52 tests
- Generator: 32 tests
- **Total: 380 tests**

## Configuration

Edit `safeops/config.py` to modify:
- Default seed
- Simulation parameters
- Profile specifications
- Enum values
- Business rules
- ID patterns

## Project Structure

```
industrial-safeops-generator/
├── safeops/
│   ├── config.py              # Configuration and constants
│   ├── generator.py           # CLI and pipeline orchestration
│   ├── validate.py            # Validation logic
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── master_gen.py      # Master data generation
│   │   ├── event_engine.py    # Event data generation
│   │   ├── anomaly_injector.py # Anomaly injection
│   │   └── sql_export.py     # SQL export functionality
│   └── tests/
│       ├── __init__.py
│       ├── test_config.py
│       ├── test_master_data.py
│       ├── test_event_engine.py
│       ├── test_anomaly_injector.py
│       ├── test_validate.py
│       └── test_generator.py
├── requirements.txt
├── README.md
├── DATA_DICTIONARY.md
└── plan.md
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

Rakesh Podishetti

GitHub: https://github.com/PodishettiRakesh

LinkedIn: https://linkedin.com/in/podisheeti-rakesh

Project Repository: https://github.com/PodishettiRakesh/industrial-safeops-generator
