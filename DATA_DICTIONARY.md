# SafeOps Generator Data Dictionary

This document provides a comprehensive data dictionary for all entities in the SafeOps Generator synthetic data system.

## Entity Overview

The system generates 10 core entities organized into two categories:

### Master/Reference Data (Static Entities)
1. **Plant** - Physical factory locations
2. **Machine** - Manufacturing equipment
3. **SafetyZone** - Protected areas around machines
4. **Interlock** - Safety protection mechanisms
5. **AlarmDefinition** - Configured alarm thresholds and rules

### Event/Transaction Data (Time-Series Entities)
6. **OperatorShift** - Operator work periods
7. **MachineStateEvent** - Machine status transitions
8. **AlarmEvent** - Threshold breach occurrences
9. **Acknowledgement** - Operator responses to alarms
10. **Incident** - Safety incidents
11. **CorrectiveAction** - Remediation actions

---

## Entity Details

### 1. Plant

**Description:** Physical factory location where machines operate.

**Primary Key:** `plant_id`

**Table: plants.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| plant_id | string | Yes | Pattern: `PLT-XXX` where XXX is 001-999 | N/A | Unique | Must match regex `^PLT-\d{3}$` | Primary key |
| plant_name | string | Yes | Factory Alpha, Factory Beta, Factory Gamma, Factory Delta, Factory Epsilon, Factory Zeta, Factory Eta, Factory Theta | N/A | Unique | Must be from predefined list | Deterministic selection via RNG |
| location | string | Yes | Detroit, MI; Chicago, IL; Houston, TX; Phoenix, AZ; Seattle, WA; Denver, CO; Atlanta, GA; Boston, MA | N/A | No | Must be from predefined list | Deterministic selection via RNG |
| created_at | timestamp | Yes | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` | UTC | No | Must be parseable, before simulation start | Fixed value: `2025-12-01T00:00:00Z` |

**Relationships:**
- `machine_id` → Machines (1:N): One plant has many machines

**Lifecycle States:** Not applicable (static reference data)

**Effective Dates:** Not applicable (static reference data)

**Unsupported Aspects:** None

---

### 2. Machine

**Description:** Manufacturing equipment that generates alarms and state events.

**Primary Key:** `machine_id`

**Foreign Key:** `plant_id` → Plants

**Table: machines.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| machine_id | string | Yes | Pattern: `MCH-XXX` where XXX is 001-999 | N/A | Unique | Must match regex `^MCH-\d{3}$` | Primary key |
| plant_id | string | Yes | Must exist in plants.plant_id | N/A | No | Foreign key integrity | References parent plant |
| machine_type | enum | Yes | CNC_Mill, Robotic_Arm, Stamping_Press, Furnace | N/A | No | Must be from MACHINE_TYPES enum | Determines model number pattern |
| model_number | string | Yes | Pattern: `{type}-MK-XXX` where type is machine_type with underscores replaced by hyphens | N/A | No | Format validation | Auto-generated from machine_type and index |
| status | enum | Yes | Operational, Maintenance, Offline | N/A | No | Must be from MACHINE_STATUS enum | All machines start as Operational |

**Relationships:**
- `plant_id` → Plants (N:1): Many machines belong to one plant
- `zone_id` ← SafetyZones (1:N): One machine has many safety zones
- `interlock_id` ← Interlocks (1:N): One machine has many interlocks
- `alarm_def_id` ← AlarmDefinitions (1:N): One machine has many alarm definitions
- `machine_id` → MachineStateEvents (1:N): One machine has many state events
- `machine_id` → Incidents (1:N): One machine has many incidents

**Lifecycle States:** Operational, Maintenance, Offline

**Effective Dates:** Not applicable (status is current state, not time-bound)

**Unsupported Aspects:** None

---

### 3. SafetyZone

**Description:** Protected areas around machines requiring safety monitoring.

**Primary Key:** `zone_id`

**Foreign Key:** `machine_id` → Machines

**Table: safety_zones.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| zone_id | string | Yes | Pattern: `SAFE-PLT-XXX-XXX` where first XXX is plant_id, second XXX is counter | N/A | Unique | Must match regex `^SAFE-PLT-\d{3}-\d{3}$` | Primary key, plant-scoped counter |
| machine_id | string | Yes | Must exist in machines.machine_id | N/A | No | Foreign key integrity | References parent machine |
| zone_type | enum | Yes | Perimeter_Laser, Pressure_Mat, Proximity_Radar | N/A | No | Must be from ZONE_TYPES enum | Type of safety detection system |
| risk_level | enum | Yes | Low, Medium, High, Critical | N/A | No | Must be from RISK_LEVELS enum | Inherent risk level of zone |

**Relationships:**
- `machine_id` → Machines (N:1): Many safety zones belong to one machine

**Lifecycle States:** Not applicable (static reference data)

**Effective Dates:** Not applicable (static reference data)

**Unsupported Aspects:** None

---

### 4. Interlock

**Description:** Safety protection mechanisms that prevent unsafe machine states.

**Primary Key:** `interlock_id`

**Foreign Key:** `machine_id` → Machines

**Table: interlocks.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| interlock_id | string | Yes | Pattern: `INT-XXXX` where XXXX is 0001-9999 | N/A | Unique | Must match regex `^INT-\d{4}$` | Primary key, global counter |
| machine_id | string | Yes | Must exist in machines.machine_id | N/A | No | Foreign key integrity | References parent machine |
| interlock_type | enum | Yes | Mechanical_Guard, Electrical_Relay, Software_E-Stop | N/A | No | Must be from INTERLOCK_TYPES enum | Type of interlock mechanism |
| normal_state | enum | Yes | Closed, Engaged, Energized | N/A | No | Must be from INTERLOCK_STATES enum | Determined by interlock_type (see config) |

**Business Rule:** Normal state is determined by interlock type:
- Mechanical_Guard → Closed
- Electrical_Relay → Engaged
- Software_E-Stop → Energized

**Relationships:**
- `machine_id` → Machines (N:1): Many interlocks belong to one machine

**Lifecycle States:** Not applicable (static reference data)

**Effective Dates:** Not applicable (static reference data)

**Unsupported Aspects:** None

---

### 5. AlarmDefinition

**Description:** Configured alarm thresholds and severity rules for machine metrics.

**Primary Key:** `alarm_def_id`

**Foreign Key:** `machine_id` → Machines

**Table: alarm_definitions.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| alarm_def_id | string | Yes | Pattern: `DEF-XXXX` where XXXX is 0001-9999 | N/A | Unique | Must match regex `^DEF-\d{4}$` | Primary key, global counter |
| machine_id | string | Yes | Must exist in machines.machine_id | N/A | No | Foreign key integrity | References parent machine |
| metric_name | enum | Yes | Temperature, Vibration, Pressure, Voltage | N/A | No | Must be from METRIC_NAMES enum | Metric being monitored |
| severity | enum | Yes | Low, Medium, High, Critical | N/A | No | Must be from SEVERITY_LEVELS enum | Alarm severity level |
| threshold_limit | float | Yes | Within metric-specific range (see config) | Metric-specific (see config) | No | Must be within METRIC_RANGES | Threshold calculated from severity |

**Metric Units and Ranges:**
- Temperature: °C, range 20.0-150.0
- Vibration: mm/s, range 0.0-50.0
- Pressure: bar, range 0.0-100.0
- Voltage: V, range 110.0-480.0

**Business Rule:** Threshold is calculated from severity:
- Low: 90% of max range
- Medium: 70% of max range
- High: 50% of max range
- Critical: 30% of max range

**Relationships:**
- `machine_id` → Machines (N:1): Many alarm definitions belong to one machine
- `alarm_def_id` → AlarmEvents (1:N): One alarm definition generates many alarm events

**Lifecycle States:** Not applicable (static reference data)

**Effective Dates:** Not applicable (static reference data)

**Unsupported Aspects:** None

---

### 6. OperatorShift

**Description:** Operator work periods covering plant operations.

**Primary Key:** `shift_id`

**Foreign Key:** `plant_id` → Plants

**Table: operator_shifts.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| shift_id | string | Yes | Pattern: `SHF-2026-XXXXX` where XXXXX is counter | N/A | Unique | Must match regex `^SHF-2026-\d{5}$` | Primary key, global counter |
| plant_id | string | Yes | Must exist in plants.plant_id | N/A | No | Foreign key integrity | References parent plant |
| operator_name | string | Yes | John Smith, Jane Doe, Bob Johnson, Alice Williams, Charlie Brown, Diana Prince, Edward Stone, Fiona Green | N/A | No | Must be from predefined list | Deterministic selection via RNG |
| start_time | timestamp | Yes | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` | UTC | No | Must be parseable, before end_time | Shift start time |
| end_time | timestamp | Yes | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` | UTC | No | Must be parseable, after start_time | Shift end time (start + 8 hours) |

**Business Rule:** Shift duration is fixed at 8 hours.

**Relationships:**
- `plant_id` → Plants (N:1): Many shifts belong to one plant
- `shift_id` → Acknowledgements (1:N): One shift has many acknowledgements

**Lifecycle States:** Not applicable (historical time-series data)

**Effective Dates:** `start_time` to `end_time`

**Unsupported Aspects:** None

---

### 7. MachineStateEvent

**Description:** Machine status transitions with interlock status.

**Primary Key:** `state_event_id` (integer)

**Foreign Key:** `machine_id` → Machines

**Table: machine_state_events.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| state_event_id | int | Yes | Positive integer, unique across all events | N/A | Unique | Must be unique, non-null | Primary key, global counter |
| machine_id | string | Yes | Must exist in machines.machine_id | N/A | No | Foreign key integrity | References parent machine |
| timestamp | timestamp | Yes | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` | UTC | No | Must be parseable, within simulation window | Event timestamp |
| previous_state | enum | Yes | Operational, Maintenance, Offline | N/A | No | Must be from MACHINE_STATUS enum | State before transition |
| new_state | enum | Yes | Operational, Maintenance, Offline | N/A | No | Must be from MACHINE_STATUS enum | State after transition |
| interlock_status | enum | Yes | Secure, Tripped, Bypassed | N/A | No | Must be from INTERLOCK_STATUS enum | Interlock state at transition |
| source_event_id | string | No | Pattern: `SRC-XXXXXX` or null | N/A | No | Format validation if present | Optional correlation ID |

**Business Rules:**
- Interlock status is correlated with machine state:
  - Operational → Secure (baseline)
  - Maintenance → Bypassed (baseline)
  - Offline → Secure or Tripped (random)
- Anomaly: IMPOSSIBLE_INTERLOCK when new_state == "Operational" AND interlock_status == "Bypassed"

**Relationships:**
- `machine_id` → Machines (N:1): Many state events belong to one machine
- State events enable incident traceability to machine state history

**Lifecycle States:** previous_state → new_state transitions

**Effective Dates:** `timestamp` represents the transition moment

**Unsupported Aspects:** None

---

### 8. AlarmEvent

**Description:** Threshold breach occurrences with metric values and interlock status.

**Primary Key:** `alarm_event_id`

**Foreign Key:** `alarm_def_id` → AlarmDefinitions

**Table: alarm_events.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| alarm_event_id | string | Yes | Pattern: `ALM-MCH-XXX-XXXXXX` where MCH-XXX is machine_id, XXXXXX is per-machine counter | N/A | Unique | Must match regex `^ALM-MCH-\d{3}-\d{6}$` | Primary key, per-machine counter |
| alarm_def_id | string | Yes | Must exist in alarm_definitions.alarm_def_id | N/A | No | Foreign key integrity | References alarm definition |
| timestamp | timestamp | Yes | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` | UTC | No | Must be parseable, within simulation window | Alarm timestamp |
| current_value | float | Yes | Within metric-specific range | Metric-specific | No | Must be within METRIC_RANGES | Metric value at alarm time |
| interlock_status | enum | Yes | Secure, Tripped, Bypassed | N/A | No | Must be from INTERLOCK_STATUS enum | Interlock status at alarm time |
| source_event_id | string | No | Pattern: `SRC-XXXXXX` or null | N/A | No | Format validation if present | Optional correlation ID |
| replay_group_id | string | No | Pattern: `RPG-XXXXXX` or null | N/A | No | Format validation if present | Non-null for REPLAY_FLOOD anomalies |

**Business Rules:**
- 70% of alarms breach threshold, 30% are near threshold (within 10%)
- Interlock status correlated with value breach:
  - Value > threshold → Secure (30%) or Tripped (70%)
  - Value ≤ threshold → Secure (100%)
- Anomaly: REPLAY_FLOOD when replay_group_id is non-null (duplicate alarm events)

**Relationships:**
- `alarm_def_id` → AlarmDefinitions (N:1): Many alarm events reference one alarm definition
- `alarm_event_id` → Acknowledgements (1:N): One alarm event has many acknowledgements
- `alarm_event_id` → Incidents (1:1 or 0:1): One incident references one alarm event (nullable for MISSING_CONTEXT anomaly)

**Lifecycle States:** Not applicable (point-in-time events)

**Effective Dates:** `timestamp` represents the alarm occurrence

**Unsupported Aspects:** None

---

### 9. Acknowledgement

**Description:** Operator responses to alarm events with shift reference.

**Primary Key:** `ack_id`

**Foreign Keys:**
- `alarm_event_id` → AlarmEvents
- `shift_id` → OperatorShifts

**Table: acknowledgements.csv`

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| ack_id | string | Yes | Pattern: `ACK-ALM-MCH-XXX-XXXXXX-XX` where middle is alarm_event_id, XX is per-alarm counter | N/A | Unique | Must match regex `^ACK-ALM-MCH-\d{3}-\d{6}-\d{2}$` | Primary key, per-alarm counter |
| alarm_event_id | string | Yes | Must exist in alarm_events.alarm_event_id | N/A | No | Foreign key integrity | References alarm event |
| shift_id | string | Yes | Must exist in operator_shifts.shift_id | N/A | No | Foreign key integrity | References operator shift |
| acknowledged_at | timestamp | Yes | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` | UTC | No | Must be parseable | Acknowledgement timestamp |

**Business Rules:**
- Only ~80% of alarms are acknowledged
- Acknowledgement delay based on severity SLA:
  - Critical: 15 minutes SLA
  - High: 30 minutes SLA
  - Medium: 60 minutes SLA
  - Low: 120 minutes SLA
- Acknowledgement must occur during an active shift at the same plant
- Anomaly: ACK_BEFORE_ALARM when acknowledged_at < alarm timestamp

**Relationships:**
- `alarm_event_id` → AlarmEvents (N:1): Many acknowledgements reference one alarm event
- `shift_id` → OperatorShifts (N:1): Many acknowledgements reference one shift

**Lifecycle States:** Not applicable (point-in-time events)

**Effective Dates:** `acknowledged_at` represents the acknowledgement time

**Unsupported Aspects:** None

---

### 10. Incident

**Description:** Safety incidents triggered by alarm events with severity classification.

**Primary Key:** `incident_id`

**Foreign Keys:**
- `machine_id` → Machines
- `alarm_event_id` → AlarmEvents (nullable)

**Table: incidents.csv**

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| incident_id | string | Yes | Pattern: `INC-2026-XXXXXX` where XXXXXX is counter | N/A | Unique | Must match regex `^INC-2026-\d{6}$` | Primary key, global counter |
| machine_id | string | Yes | Must exist in machines.machine_id | N/A | No | Foreign key integrity | References machine where incident occurred |
| alarm_event_id | string | No | Must exist in alarm_events.alarm_event_id if not null | N/A | No | Foreign key integrity if present | References triggering alarm (nullable for MISSING_CONTEXT anomaly) |
| severity_level | enum | Yes | Major, Critical, Catastrophic | N/A | No | Must be from INCIDENT_SEVERITY enum | Incident severity |
| logged_at | timestamp | Yes | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` | UTC | No | Must be parseable | Incident log timestamp |
| issue_type | string | Yes | Safety Interlock Bypass, Overpressure Condition, Temperature Excursion, Mechanical Failure, Electrical Fault, Unauthorized Access | N/A | No | Must be from predefined list | Incident classification |

**Business Rules:**
- Incident eligibility conditions:
  1. Critical alarm with Tripped interlock
  2. High or Critical alarm with value > 2x threshold
  3. Any alarm with Tripped interlock (30% probability)
- Only ~50% of qualifying alarms become incidents
- Severity level based on alarm severity:
  - Critical alarm → Critical (70%) or Catastrophic (30%)
  - High alarm → Major (60%) or Critical (40%)
  - Other alarms → Major
- Anomaly: MISSING_CONTEXT when alarm_event_id is null

**Traceability:**
- `machine_id` → Machines enables traceability to machine state history via MachineStateEvent
- `alarm_event_id` → AlarmEvents enables traceability to triggering alarm
- `incident_id` → CorrectiveActions enables traceability to remediation actions

**Relationships:**
- `machine_id` → Machines (N:1): Many incidents belong to one machine
- `alarm_event_id` → AlarmEvents (N:1 or 0:1): Many incidents reference one alarm event (nullable)
- `incident_id` → CorrectiveActions (1:N): One incident has many corrective actions

**Lifecycle States:** Not applicable (historical record)

**Effective Dates:** `logged_at` represents when incident was recorded

**Unsupported Aspects:** None

---

### 11. CorrectiveAction

**Description:** Remediation actions taken in response to incidents.

**Primary Key:** `action_id`

**Foreign Key:** `incident_id` → Incidents

**Table: corrective_actions.csv`

| Field | Data Type | Required | Allowed Values | Units | Uniqueness | Validation Rules | Notes |
|-------|-----------|----------|----------------|-------|------------|------------------|-------|
| action_id | string | Yes | Pattern: `ACT-INC-2026-XXXXXX-XX` where middle is incident_id, XX is per-incident counter | N/A | Unique | Must match regex `^ACT-INC-2026-\d{6}-\d{2}$` | Primary key, per-incident counter |
| incident_id | string | Yes | Must exist in incidents.incident_id | N/A | No | Foreign key integrity | References parent incident |
| action_taken | string | Yes | Reset safety interlock, Replace worn component, Adjust parameter settings, Perform maintenance inspection, Update control software, Repair electrical connection, Clean sensor housing, Recalibrate instrumentation | N/A | No | Must be from predefined list | Action description |
| status | enum | Yes | Open, In_Progress, Closed | N/A | No | Must be from ACTION_STATUS enum | Action status |
| verified_at | timestamp | No | ISO 8601 format: `%Y-%m-%dT%H:%M:%SZ` or null | UTC | No | Must be parseable if present | Verification timestamp (nullable for UNVERIFIED_CLOSURE anomaly) |

**Business Rules:**
- 1-3 actions per incident
- Status lifecycle distribution: Open (40%), In_Progress (30%), Closed (30%)
- Closed actions must have verified_at timestamp (baseline)
- Anomaly: UNVERIFIED_CLOSURE when status == "Closed" AND verified_at is null
- verified_at must be after incident logged_at (baseline)

**Relationships:**
- `incident_id` → Incidents (N:1): Many corrective actions belong to one incident

**Lifecycle States:** Open → In_Progress → Closed

**Effective Dates:** `verified_at` represents when action was verified (if applicable)

**Unsupported Aspects:** None

---

## Relationship Cardinalities

| Parent Entity | Child Entity | Cardinality | Notes |
|---------------|--------------|-------------|-------|
| Plant | Machine | 1:N | One plant has many machines |
| Machine | SafetyZone | 1:N | One machine has 1-3 safety zones |
| Machine | Interlock | 1:N | One machine has 2-4 interlocks |
| Machine | AlarmDefinition | 1:N | One machine has many alarm definitions |
| Machine | MachineStateEvent | 1:N | One machine has 50-200 state events |
| Machine | Incident | 1:N | One machine has many incidents |
| Plant | OperatorShift | 1:N | One plant has many shifts (continuous coverage) |
| AlarmDefinition | AlarmEvent | 1:N | One definition generates many events |
| AlarmEvent | Acknowledgement | 1:N | One event has 0 or many acknowledgements |
| AlarmEvent | Incident | 1:1 or 0:1 | One event may trigger one incident (nullable) |
| Incident | CorrectiveAction | 1:N | One incident has 1-3 actions |

**Note:** No many-to-many relationships requiring bridge tables in this schema.

---

## ID Format Conventions

| Entity | ID Pattern | Example | Counter Scope |
|--------|-----------|---------|---------------|
| Plant | PLT-XXX | PLT-001 | Per-profile |
| Machine | MCH-XXX | MCH-001 | Per-profile |
| SafetyZone | SAFE-PLT-XXX-XXX | SAFE-PLT-001-001 | Per-plant |
| Interlock | INT-XXXX | INT-0001 | Global |
| AlarmDefinition | DEF-XXXX | DEF-0001 | Global |
| OperatorShift | SHF-2026-XXXXX | SHF-2026-00001 | Global |
| MachineStateEvent | integer | 12345 | Global |
| AlarmEvent | ALM-MCH-XXX-XXXXXX | ALM-MCH-001-000001 | Per-machine |
| Acknowledgement | ACK-ALM-MCH-XXX-XXXXXX-XX | ACK-ALM-MCH-001-000001-01 | Per-alarm-event |
| Incident | INC-2026-XXXXXX | INC-2026-000001 | Global |
| CorrectiveAction | ACT-INC-2026-XXXXXX-XX | ACT-INC-2026-000001-01 | Per-incident |

**Notes:**
- All counters are zero-padded to ensure deterministic sorting
- IDs are immutable once generated
- Referenced IDs are exactly consistent across files

---

## Anomaly Detection Rules

### ACK_BEFORE_ALARM
- **Detection:** `acknowledged_at < alarm_timestamp`
- **Target Table:** acknowledgements
- **Entity ID:** ack_id
- **Business Rule:** Acknowledgements must occur after alarms

### IMPOSSIBLE_INTERLOCK
- **Detection:** `new_state == "Operational" AND interlock_status == "Bypassed"`
- **Target Table:** machine_state_events
- **Entity ID:** state_event_id (as string)
- **Business Rule:** Operational machines must have Secure interlock

### MISSING_CONTEXT
- **Detection:** `alarm_event_id is null`
- **Target Table:** incidents
- **Entity ID:** incident_id
- **Business Rule:** Incidents should reference triggering alarm events

### REPLAY_FLOOD
- **Detection:** `replay_group_id is not null` (grouped records indicate duplicates)
- **Target Table:** alarm_events
- **Entity ID:** alarm_event_id
- **Business Rule:** Each alarm event should be unique (no replay attacks)

### UNVERIFIED_CLOSURE
- **Detection:** `status == "Closed" AND verified_at is null`
- **Target Table:** corrective_actions
- **Entity ID:** action_id
- **Business Rule:** Closed actions must have verification timestamps

---

## Nuisance Alarm Cluster Detection

**Definition:** Groups of 5 or more Low or Medium severity alarms from the same machine occurring within a 10-minute window.

**Detection Rule:**
1. Filter alarm events for Low/Medium severity (from alarm_definitions)
2. Group by machine_id
3. Apply sliding window (10 minutes) to find 5+ alarms in window
4. Record cluster ID, machine_id, alarm count, and time window

**Operational Significance:** Indicates repeated minor issues that may mask genuine safety problems or indicate equipment requiring maintenance.

**Validation Report:** Includes cluster count, affected machines, and cluster details.

---

## Ground Truth Schema

**File:** ground_truth.csv

**Columns:**
- `target_table` (string): Name of affected table
- `entity_id` (string): Primary key of affected record
- `anomaly_type` (string): One of the five anomaly categories
- `description` (string): Explanation of the violation

**Design Principles:**
- One label per affected record per anomaly category
- Stable deterministic ordering (by target_table, entity_id)
- No ground-truth labels embedded in operational tables
- Descriptions explain violations without exposing unnecessary data

---

## Unsupported Features

The following features are **not supported** in the current implementation:

1. **External Database Integration:** CSV-only export (no direct database export)
2. **SQL Seed Data Export:** Not implemented (CSV and JSON only)
3. **Effective Date Ranges:** Entities do not have effective start/end dates (current state only)
4. **Bridge Tables:** No many-to-many relationships requiring bridge tables
5. **Lifecycle State Transitions:** Status changes are recorded as events, not state transitions with effective dates
6. **Time Travel Queries:** Historical state queries require joining event tables (no current state table)
7. **Multitenancy:** No tenant isolation or organization-level scoping
8. **Audit Trail:** No explicit audit trail table (changes are event records)
9. **Soft Deletes:** No soft delete mechanism (records are immutable)
10. **Versioning:** No entity versioning or change history tables

---

## Validation Summary

All entities undergo comprehensive validation:

1. **Structural Integrity:**
   - Required tables and columns exist
   - Primary keys are non-null and unique
   - Foreign keys resolve to existing records
   - Enum values are valid
   - Timestamps are parseable
   - Row counts match profile targets

2. **Business Rules:**
   - Independent detection of all five anomaly categories
   - Nuisance alarm cluster identification
   - Comparison with ground truth labels
   - Reconciliation metrics (matched, missed, unlabelled)

3. **Data Quality:**
   - ID format validation via regex patterns
   - Referential integrity across all foreign keys
   - Enum constraint validation
   - Timestamp ordering validation
   - Null constraint validation

---

## Generation Volume

### DEV Profile
- Plants: 2
- Machines: 5
- Alarm Definitions: 10
- Alarm Events: 500
- Simulation Window: 30 days (shortened for faster testing)

### FULL Profile
- Plants: 4
- Machines: 60
- Alarm Definitions: 200
- Alarm Events: 50,000
- Simulation Window: 30 days

---

## Reproducibility

- Same seed → identical data (byte-for-byte)
- Different seed → different random values, same structure
- Default seed: 20261022
- Verification command: `python -m safeops.generator --profile full --verify-reproducibility`

**Note:** Reproducibility is guaranteed within the same environment. Dependency versions are recorded in manifest.json. Changes in dependency versions may affect output.
