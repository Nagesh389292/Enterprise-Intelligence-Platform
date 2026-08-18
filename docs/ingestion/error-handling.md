# Fault Tolerance, Error Handling & Quarantine Runbooks
### NexaCore Enterprise Intelligence Platform

---

## 1. Error Classification Matrix

The ingestion framework categorizes errors into two distinct operational classes:

```text
                                INGESTION ERROR TAXONOMY
   ┌────────────────────────────────────────────────────────────────────────────────┐
   │ 1. Transient Errors (Network timeout, DB lock wait, temporary connection drop) │
   │    -> Strategy: Automatic Retry with Exponential Backoff + Jitter              │
   ├────────────────────────────────────────────────────────────────────────────────┤
   │ 2. Permanent Data Errors (Invalid schema, null PK, corrupt JSON, bad FK)       │
   │    -> Strategy: Quarantine Isolation to audit.quarantine_records               │
   └────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Automatic Retry Engine & Exponential Backoff

For **Transient Errors** (e.g., PostgreSQL connection pool exhaustion), the ingestion pipeline applies an exponential backoff retry loop:

$$T_{\text{wait}} = \min\left(T_{\text{max}}, T_{\text{base}} \times 2^{\text{attempt}} + \text{random\_jitter}\right)$$

* **Max Retry Attempts**: 3 attempts.
* **Base Delay**: 2 seconds.
* **Max Delay Cap**: 30 seconds.
* **Behavior**: If all 3 retry attempts fail, the execution batch status is marked `FAILED` in `audit.pipeline_execution_logs`, alerting operators.

---

## 3. Quarantine Dead-Letter Isolation

For **Permanent Data Errors** (e.g., negative quantity, malformed date string):
1. The defective row is diverted to `audit.quarantine_records` as a `JSONB` document.
2. The remaining valid rows within the batch proceed to Silver tables.
3. Pipeline execution continues without crashing the batch.

---

## 4. Disaster Recovery & Quarantine Replay Runbook

When upstream systems fix data defects, operators replay quarantined records using the **Quarantine Replay CLI**:

```text
                  QUARANTINE REPLAY WORKFLOW
 ┌────────────────────────────────────────────────────────┐
 │ 1. Query audit.quarantine_records WHERE entity = 'orders'
 ├────────────────────────────────────────────────────────┤
 │ 2. Apply patch SQL / Python fix script                 │
 ├────────────────────────────────────────────────────────┤
 │ 3. Re-submit fixed records to Validation Gate          │
 ├────────────────────────────────────────────────────────┤
 │ 4. Insert valid records into source.orders             │
 ├────────────────────────────────────────────────────────┤
 │ 5. DELETE replayed records from audit.quarantine_records│
 └────────────────────────────────────────────────────────┘
```
