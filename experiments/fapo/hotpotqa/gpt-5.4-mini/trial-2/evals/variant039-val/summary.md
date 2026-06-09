# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 75.72

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.058 | 0.677 | 1.692 |
| summarize_hop1 | 2.314 | 2.162 | 3.525 |
| query_hop2 | 1.289 | 1.118 | 2.243 |
| retrieve_hop2 | 1.345 | 1.520 | 1.642 |
| summarize_hop2 | 1.718 | 1.537 | 2.681 |
| answer | 0.940 | 0.841 | 1.636 |
| **Total** | **8.664** | **8.168** | **12.382** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
