# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 74.84

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.139 | 0.002 | 0.129 |
| summarize_hop1 | 1.359 | 1.290 | 1.998 |
| query_hop2 | 1.086 | 1.023 | 1.533 |
| retrieve_hop2 | 0.484 | 0.002 | 1.662 |
| summarize_hop2 | 1.534 | 1.440 | 2.265 |
| answer | 0.828 | 0.751 | 1.102 |
| **Total** | **5.430** | **4.822** | **7.726** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
