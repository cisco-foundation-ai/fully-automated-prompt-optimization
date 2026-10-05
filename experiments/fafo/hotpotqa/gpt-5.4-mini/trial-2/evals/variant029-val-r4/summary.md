# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.23

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.011 |
| summarize_hop1 | 2.480 | 2.198 | 4.364 |
| query_hop2 | 1.480 | 1.168 | 2.516 |
| retrieve_hop2 | 0.323 | 0.002 | 1.564 |
| summarize_hop2 | 2.094 | 1.623 | 3.453 |
| answer | 1.073 | 0.879 | 1.761 |
| **Total** | **7.477** | **6.402** | **13.376** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
