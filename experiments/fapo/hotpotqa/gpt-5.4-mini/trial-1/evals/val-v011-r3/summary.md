# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 77.17

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.105 | 0.002 | 0.110 |
| summarize_hop1 | 1.397 | 1.294 | 2.169 |
| query_hop2 | 1.093 | 1.050 | 1.451 |
| retrieve_hop2 | 0.433 | 0.002 | 1.605 |
| summarize_hop2 | 1.638 | 1.530 | 2.348 |
| answer | 0.856 | 0.746 | 1.204 |
| **Total** | **5.522** | **4.994** | **8.018** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
| query_hop2 | 1 |
