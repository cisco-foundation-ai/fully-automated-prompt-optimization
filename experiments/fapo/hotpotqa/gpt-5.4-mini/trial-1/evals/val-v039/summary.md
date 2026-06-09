# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.145 | 0.002 | 0.121 |
| summarize_hop1 | 1.454 | 1.317 | 2.409 |
| query_hop2 | 1.164 | 1.097 | 1.655 |
| retrieve_hop2 | 0.723 | 0.003 | 1.633 |
| summarize_hop2 | 1.662 | 1.562 | 2.498 |
| answer | 0.806 | 0.749 | 1.153 |
| **Total** | **5.953** | **5.533** | **8.444** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
