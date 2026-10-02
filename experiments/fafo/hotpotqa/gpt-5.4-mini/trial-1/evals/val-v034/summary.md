# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.10

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.128 | 0.002 | 0.135 |
| summarize_hop1 | 1.314 | 1.224 | 1.920 |
| query_hop2 | 1.135 | 1.057 | 1.743 |
| retrieve_hop2 | 0.392 | 0.002 | 1.408 |
| summarize_hop2 | 1.593 | 1.526 | 2.352 |
| answer | 0.790 | 0.758 | 1.166 |
| **Total** | **5.352** | **4.864** | **7.793** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
