# Evaluation Summary

Total cases: 300

## Composite Score
- average: 27.00

## Score Breakdown
- num_found: 1.97
- num_gold: 3.00
- partial_recall: 65.78
- recall: 27.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.005 |
| summarize_hop1 | 3.136 | 2.920 | 4.641 |
| query_hop2 | 0.707 | 0.554 | 1.004 |
| retrieve_hop2 | 0.293 | 0.002 | 1.425 |
| summarize_hop2 | 3.622 | 3.117 | 5.786 |
| query_hop3 | 0.875 | 0.573 | 1.275 |
| retrieve_hop3 | 0.250 | 0.002 | 1.424 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.910** | **7.867** | **16.437** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 219 |
