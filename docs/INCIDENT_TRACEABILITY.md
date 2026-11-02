# Incident Traceability

Incidents can be traced to relevant machine-state history and corrective actions through foreign key relationships.

## Traceability Paths

### 1. Incident → Machine State History

View machine state transitions leading up to an incident.

```sql
SELECT
    mse.state_event_id,
    mse.timestamp,
    mse.previous_state,
    mse.new_state,
    mse.interlock_status
FROM machine_state_events mse
WHERE mse.machine_id = 'MCH-001'
  AND mse.timestamp <= '2026-01-15T12:00:00Z'
ORDER BY mse.timestamp DESC
LIMIT 10;
```

### 2. Incident → Triggering Alarm

Identify the alarm that triggered an incident.

```sql
SELECT
    ae.alarm_event_id,
    ae.timestamp,
    ad.metric_name,
    ad.severity,
    ae.current_value,
    ad.threshold_limit
FROM alarm_events ae
JOIN alarm_definitions ad ON ae.alarm_def_id = ad.alarm_def_id
WHERE ae.alarm_event_id = 'ALM-MCH-001-000116';
```

### 3. Incident → Corrective Actions

View all remediation actions taken for an incident.

```sql
SELECT
    ca.action_id,
    ca.action_taken,
    ca.status,
    ca.verified_at
FROM corrective_actions ca
WHERE ca.incident_id = 'INC-2026-000032'
ORDER BY ca.action_id;
```

## Notes

- For incidents with MISSING_CONTEXT anomaly (alarm_event_id is null), the triggering alarm cannot be traced.
- The machine state history query uses a LIMIT to avoid returning excessive rows for long-running incidents.
- Adjust the machine_id, timestamp, and incident_id values to match your specific incident of interest.
