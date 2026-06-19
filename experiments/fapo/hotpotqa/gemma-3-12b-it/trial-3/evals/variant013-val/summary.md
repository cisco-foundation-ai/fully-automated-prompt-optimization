# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.00

## Score Breakdown
- exact_match: 60.00
- f1: 68.81

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.009 |
| summarize_hop1 | 1.757 | 1.556 | 3.074 |
| query_hop2 | 0.976 | 0.943 | 1.311 |
| retrieve_hop2 | 0.832 | 1.044 | 1.611 |
| summarize_hop2 | 2.763 | 2.708 | 4.365 |
| answer | 0.932 | 0.885 | 1.434 |
| **Total** | **7.279** | **6.973** | **10.653** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 120 |
