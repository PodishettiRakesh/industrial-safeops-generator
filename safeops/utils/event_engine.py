"""
Event engine module.

This module generates OperatorShift, MachineStateEvent, AlarmEvent,
Acknowledgement, Incident, and CorrectiveAction entities.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict
from safeops.config import (
    get_profile,
    SHIFT_DURATION_HOURS,
    ACKNOWLEDGEMENT_SLAS,
    MACHINE_STATUS,
    INTERLOCK_STATUS,
    INCIDENT_SEVERITY,
    ACTION_STATUS,
    SIMULATION_START_UTC,
    SIMULATION_DAYS,
    TIMESTAMP_FORMAT
)


def generate_events(
    master_data: Dict[str, pd.DataFrame],
    profile: str,
    rng: np.random.Generator
) -> Dict[str, pd.DataFrame]:
    """
    Generate all event entities using master data references.

    Args:
        master_data: Dictionary of master DataFrames.
        profile: Profile name ('dev' or 'full').
        rng: Random number generator.

    Returns:
        Dictionary of event DataFrames keyed by entity name.
    """
    profile_config = get_profile(profile)

    # Extract master data
    plants = master_data["plants"]
    machines = master_data["machines"]
    alarm_definitions = master_data["alarm_definitions"]

    # Calculate simulation time range
    sim_start = datetime.fromisoformat(SIMULATION_START_UTC.replace("Z", "+00:00"))
    sim_end = sim_start + timedelta(days=SIMULATION_DAYS)

    # Generate in dependency order
    operator_shifts = generate_operator_shifts(plants, sim_start, sim_end, rng)
    machine_state_events = generate_machine_state_events(machines, sim_start, sim_end, rng)
    alarm_events = generate_alarm_events(
        alarm_definitions,
        profile_config["num_alarm_events"],
        sim_start,
        sim_end,
        rng
    )
    acknowledgements = generate_acknowledgements(
        alarm_events,
        operator_shifts,
        plants,
        machines,
        alarm_definitions,
        rng
    )
    incidents = generate_incidents(
        alarm_events,
        machine_state_events,
        machines,
        sim_start,
        sim_end,
        rng
    )
    corrective_actions = generate_corrective_actions(incidents, rng)

    return {
        "operator_shifts": operator_shifts,
        "machine_state_events": machine_state_events,
        "alarm_events": alarm_events,
        "acknowledgements": acknowledgements,
        "incidents": incidents,
        "corrective_actions": corrective_actions
    }


def generate_operator_shifts(
    plants: pd.DataFrame,
    sim_start: datetime,
    sim_end: datetime,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate OperatorShift entities.

    Args:
        plants: DataFrame of plants.
        sim_start: Simulation start datetime.
        sim_end: Simulation end datetime.
        rng: Random number generator.

    Returns:
        DataFrame with columns: shift_id, plant_id, operator_name, start_time, end_time
    """
    operator_names = [
        "John Smith", "Jane Doe", "Bob Johnson", "Alice Williams",
        "Charlie Brown", "Diana Prince", "Edward Stone", "Fiona Green"
    ]

    data = []
    shift_counter = 0

    for _, plant in plants.iterrows():
        plant_id = plant["plant_id"]

        # Generate shifts covering the simulation window
        current_time = sim_start
        while current_time < sim_end:
            shift_counter += 1
            shift_id = f"SHF-2026-{shift_counter:05d}"

            # Select operator name using RNG
            operator_name = operator_names[rng.integers(0, len(operator_names))]

            start_time = current_time.strftime(TIMESTAMP_FORMAT)
            end_time = (current_time + timedelta(hours=SHIFT_DURATION_HOURS)).strftime(TIMESTAMP_FORMAT)

            data.append({
                "shift_id": shift_id,
                "plant_id": plant_id,
                "operator_name": operator_name,
                "start_time": start_time,
                "end_time": end_time
            })

            current_time += timedelta(hours=SHIFT_DURATION_HOURS)

    df = pd.DataFrame(data)
    df = df.sort_values(["start_time", "shift_id"]).reset_index(drop=True)
    return df


def generate_machine_state_events(
    machines: pd.DataFrame,
    sim_start: datetime,
    sim_end: datetime,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate MachineStateEvent entities.

    Args:
        machines: DataFrame of machines.
        sim_start: Simulation start datetime.
        sim_end: Simulation end datetime.
        rng: Random number generator.

    Returns:
        DataFrame with columns: state_event_id, machine_id, timestamp, previous_state,
                                new_state, interlock_status, source_event_id
    """
    data = []
    state_event_counter = 0

    for _, machine in machines.iterrows():
        machine_id = machine["machine_id"]

        # Generate state transitions distributed across simulation window
        num_events = rng.integers(50, 200)  # 50-200 events per machine

        current_state = "Operational"
        current_time = sim_start

        for _ in range(num_events):
            state_event_counter += 1
            state_event_id = state_event_counter

            # Select new state (allow staying in same state)
            new_state = MACHINE_STATUS[rng.integers(0, len(MACHINE_STATUS))]

            # Interlock status based on state
            if new_state == "Operational":
                interlock_status = "Secure"
            elif new_state == "Maintenance":
                interlock_status = "Bypassed"
            else:  # Offline
                interlock_status = rng.choice(["Secure", "Tripped"])

            # Advance time randomly
            time_delta = timedelta(minutes=int(rng.integers(1, 60)))
            current_time = min(current_time + time_delta, sim_end)

            timestamp = current_time.strftime(TIMESTAMP_FORMAT)

            # Source event ID for correlation (can be null)
            source_event_id = f"SRC-{state_event_counter:06d}" if rng.random() > 0.3 else None

            data.append({
                "state_event_id": state_event_id,
                "machine_id": machine_id,
                "timestamp": timestamp,
                "previous_state": current_state,
                "new_state": new_state,
                "interlock_status": interlock_status,
                "source_event_id": source_event_id
            })

            current_state = new_state

    df = pd.DataFrame(data)
    df = df.sort_values(["timestamp", "state_event_id"]).reset_index(drop=True)
    return df


def generate_alarm_events(
    alarm_definitions: pd.DataFrame,
    num_events: int,
    sim_start: datetime,
    sim_end: datetime,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate AlarmEvent entities.

    Args:
        alarm_definitions: DataFrame of alarm definitions.
        num_events: Number of alarm events to generate.
        sim_start: Simulation start datetime.
        sim_end: Simulation end datetime.
        rng: Random number generator.

    Returns:
        DataFrame with columns: alarm_event_id, alarm_def_id, timestamp, current_value,
                                interlock_status, source_event_id, replay_group_id
    """
    alarm_defs = alarm_definitions.to_dict("records")
    machine_alarm_counters = {}  # Track counter per machine

    data = []

    for i in range(num_events):
        # Select alarm definition
        alarm_def = alarm_defs[rng.integers(0, len(alarm_defs))]
        alarm_def_id = alarm_def["alarm_def_id"]
        machine_id = alarm_def["machine_id"]
        threshold = alarm_def["threshold_limit"]

        # Increment counter for this machine
        if machine_id not in machine_alarm_counters:
            machine_alarm_counters[machine_id] = 0
        machine_alarm_counters[machine_id] += 1

        alarm_event_id = f"ALM-{machine_id}-{machine_alarm_counters[machine_id]:06d}"

        # Generate timestamp distributed across simulation window
        total_seconds = (sim_end - sim_start).total_seconds()
        random_seconds = int(rng.integers(0, int(total_seconds)))
        timestamp = (sim_start + timedelta(seconds=random_seconds)).strftime(TIMESTAMP_FORMAT)

        # Generate current value (can breach threshold or be near it)
        # 70% of alarms breach threshold, 30% are near
        if rng.random() < 0.7:
            # Breach threshold
            current_value = threshold + rng.uniform(0.1, threshold * 0.5)
        else:
            # Near threshold (within 10%)
            current_value = threshold - rng.uniform(0, threshold * 0.1)

        # Interlock status correlated with value breach
        if current_value > threshold:
            interlock_status = rng.choice(["Secure", "Tripped"], p=[0.3, 0.7])
        else:
            interlock_status = "Secure"

        # Source event ID for correlation
        source_event_id = f"SRC-{i:06d}" if rng.random() > 0.4 else None

        # replay_group_id initially null (filled in Phase 4)
        replay_group_id = None

        data.append({
            "alarm_event_id": alarm_event_id,
            "alarm_def_id": alarm_def_id,
            "timestamp": timestamp,
            "current_value": round(current_value, 2),
            "interlock_status": interlock_status,
            "source_event_id": source_event_id,
            "replay_group_id": replay_group_id
        })

    df = pd.DataFrame(data)
    df = df.sort_values(["timestamp", "alarm_event_id"]).reset_index(drop=True)
    return df


def generate_acknowledgements(
    alarm_events: pd.DataFrame,
    operator_shifts: pd.DataFrame,
    plants: pd.DataFrame,
    machines: pd.DataFrame,
    alarm_definitions: pd.DataFrame,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate Acknowledgement entities.

    Args:
        alarm_events: DataFrame of alarm events.
        operator_shifts: DataFrame of operator shifts.
        plants: DataFrame of plants.
        machines: DataFrame of machines.
        alarm_definitions: DataFrame of alarm definitions.
        rng: Random number generator.

    Returns:
        DataFrame with columns: ack_id, alarm_event_id, shift_id, acknowledged_at
    """
    # Create lookup: alarm_def_id -> machine_id
    def_to_machine = dict(zip(alarm_definitions["alarm_def_id"], alarm_definitions["machine_id"]))

    # Create lookup: machine_id -> plant_id
    machine_to_plant = dict(zip(machines["machine_id"], machines["plant_id"]))

    # Only acknowledge ~80% of alarms
    alarm_events_list = alarm_events.to_dict("records")
    num_acks = int(len(alarm_events_list) * 0.8)
    selected_alarms = alarm_events_list[:num_acks]

    data = []
    ack_counter = {}  # Track ack counter per alarm

    for alarm in selected_alarms:
        alarm_event_id = alarm["alarm_event_id"]
        alarm_def_id = alarm["alarm_def_id"]
        alarm_timestamp = datetime.fromisoformat(alarm["timestamp"].replace("Z", "+00:00"))

        # Get machine_id from alarm definition
        machine_id = def_to_machine.get(alarm_def_id)
        if machine_id is None:
            continue

        plant_id = machine_to_plant.get(machine_id)
        if plant_id is None:
            continue

        # Select severity-based delay
        severity = rng.choice(["Low", "Medium", "High", "Critical"])
        sla_minutes = ACKNOWLEDGEMENT_SLAS[severity]
        delay_minutes = int(rng.integers(1, sla_minutes * 2))

        acknowledged_at = (alarm_timestamp + timedelta(minutes=delay_minutes)).strftime(TIMESTAMP_FORMAT)

        # Find shift covering this time at the same plant
        plant_shifts = operator_shifts[operator_shifts["plant_id"] == plant_id]
        if len(plant_shifts) == 0:
            continue

        # Find shift where acknowledged_at is within shift window
        ack_time = datetime.fromisoformat(acknowledged_at.replace("Z", "+00:00"))
        valid_shifts = plant_shifts[
            (pd.to_datetime(plant_shifts["start_time"]) <= ack_time) &
            (pd.to_datetime(plant_shifts["end_time"]) >= ack_time)
        ]

        if len(valid_shifts) == 0:
            # Use the shift that starts closest to acknowledgement time
            plant_shifts_sorted = plant_shifts.sort_values("start_time")
            valid_shifts = plant_shifts_sorted[
                pd.to_datetime(plant_shifts_sorted["start_time"]) <= ack_time
            ].tail(1)

        if len(valid_shifts) == 0:
            continue

        shift_id = valid_shifts.iloc[0]["shift_id"]

        # Increment ack counter for this alarm
        if alarm_event_id not in ack_counter:
            ack_counter[alarm_event_id] = 0
        ack_counter[alarm_event_id] += 1

        ack_id = f"ACK-{alarm_event_id}-{ack_counter[alarm_event_id]:02d}"

        data.append({
            "ack_id": ack_id,
            "alarm_event_id": alarm_event_id,
            "shift_id": shift_id,
            "acknowledged_at": acknowledged_at
        })

    df = pd.DataFrame(data)
    df = df.sort_values(["acknowledged_at", "ack_id"]).reset_index(drop=True)
    return df


def generate_incidents(
    alarm_events: pd.DataFrame,
    machine_state_events: pd.DataFrame,
    machines: pd.DataFrame,
    sim_start: datetime,
    sim_end: datetime,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate Incident entities.

    Args:
        alarm_events: DataFrame of alarm events.
        machine_state_events: DataFrame of machine state events.
        machines: DataFrame of machines.
        sim_start: Simulation start datetime.
        sim_end: Simulation end datetime.
        rng: Random number generator.

    Returns:
        DataFrame with columns: incident_id, machine_id, alarm_event_id, severity_level,
                                logged_at, issue_type
    """
    # Generate ~50-100 incidents
    num_incidents = rng.integers(50, 100)

    machine_ids = machines["machine_id"].tolist()
    alarm_events_list = alarm_events.to_dict("records")

    data = []
    incident_counter = 0

    for i in range(num_incidents):
        incident_counter += 1
        incident_id = f"INC-2026-{incident_counter:06d}"

        # Select machine
        machine_id = machine_ids[rng.integers(0, len(machine_ids))]

        # Select alarm event (70% have alarm, 30% missing for MISSING_CONTEXT anomaly)
        if rng.random() < 0.7:
            alarm_event = alarm_events_list[rng.integers(0, len(alarm_events_list))]
            alarm_event_id = alarm_event["alarm_event_id"]
            logged_at = alarm_event["timestamp"]
        else:
            alarm_event_id = None  # Missing context
            # Generate timestamp
            total_seconds = (sim_end - sim_start).total_seconds()
            random_seconds = int(rng.integers(0, int(total_seconds)))
            logged_at = (sim_start + timedelta(seconds=random_seconds)).strftime(TIMESTAMP_FORMAT)

        # Severity level
        severity_level = INCIDENT_SEVERITY[rng.integers(0, len(INCIDENT_SEVERITY))]

        # Issue type classification
        issue_types = [
            "Safety Interlock Bypass",
            "Overpressure Condition",
            "Temperature Excursion",
            "Mechanical Failure",
            "Electrical Fault",
            "Unauthorized Access"
        ]
        issue_type = issue_types[rng.integers(0, len(issue_types))]

        data.append({
            "incident_id": incident_id,
            "machine_id": machine_id,
            "alarm_event_id": alarm_event_id,
            "severity_level": severity_level,
            "logged_at": logged_at,
            "issue_type": issue_type
        })

    df = pd.DataFrame(data)
    df = df.sort_values(["logged_at", "incident_id"]).reset_index(drop=True)
    return df


def generate_corrective_actions(
    incidents: pd.DataFrame,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate CorrectiveAction entities.

    Args:
        incidents: DataFrame of incidents.
        rng: Random number generator.

    Returns:
        DataFrame with columns: action_id, incident_id, action_taken, status, verified_at
    """
    action_descriptions = [
        "Reset safety interlock",
        "Replace worn component",
        "Adjust parameter settings",
        "Perform maintenance inspection",
        "Update control software",
        "Repair electrical connection",
        "Clean sensor housing",
        "Recalibrate instrumentation"
    ]

    data = []

    for _, incident in incidents.iterrows():
        incident_id = incident["incident_id"]

        # Generate 1-3 actions per incident
        num_actions = rng.integers(1, 4)

        for i in range(num_actions):
            action_id = f"ACT-{incident_id}-{i+1:02d}"

            # Select action description
            action_taken = action_descriptions[rng.integers(0, len(action_descriptions))]

            # Status lifecycle distribution
            status = rng.choice(ACTION_STATUS, p=[0.4, 0.3, 0.3])

            # verified_at for Closed status
            if status == "Closed":
                # Generate verification timestamp (can be null for UNVERIFIED_CLOSURE anomaly)
                if rng.random() < 0.8:  # 80% of closed actions have verification
                    logged_at = datetime.fromisoformat(incident["logged_at"].replace("Z", "+00:00"))
                    verified_at = (logged_at + timedelta(hours=int(rng.integers(1, 48)))).strftime(TIMESTAMP_FORMAT)
                else:
                    verified_at = None  # Will be used for UNVERIFIED_CLOSURE anomaly
            else:
                verified_at = None

            data.append({
                "action_id": action_id,
                "incident_id": incident_id,
                "action_taken": action_taken,
                "status": status,
                "verified_at": verified_at
            })

    df = pd.DataFrame(data)
    df = df.sort_values(["incident_id", "action_id"]).reset_index(drop=True)
    return df
