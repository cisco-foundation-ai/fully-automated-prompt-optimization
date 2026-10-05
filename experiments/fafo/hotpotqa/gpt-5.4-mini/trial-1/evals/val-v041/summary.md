# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 77.45

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.126 | 0.002 | 0.111 |
| summarize_hop1 | 1.380 | 1.284 | 2.147 |
| query_hop2 | 1.097 | 1.034 | 1.429 |
| retrieve_hop2 | 0.405 | 0.002 | 1.556 |
| summarize_hop2 | 1.657 | 1.522 | 2.350 |
| answer | 0.820 | 0.748 | 1.255 |
| **Total** | **5.484** | **4.832** | **7.926** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
