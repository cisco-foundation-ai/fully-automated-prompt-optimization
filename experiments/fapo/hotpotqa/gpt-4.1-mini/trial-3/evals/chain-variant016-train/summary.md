# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 76.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.038 |
| summarize_hop1 | 2.772 | 2.450 | 4.989 |
| query_hop2 | 1.496 | 1.357 | 2.293 |
| retrieve_hop2 | 0.654 | 0.068 | 1.714 |
| summarize_hop2 | 2.372 | 2.137 | 4.199 |
| answer | 1.122 | 1.030 | 1.752 |
| **Total** | **8.456** | **7.988** | **12.480** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
