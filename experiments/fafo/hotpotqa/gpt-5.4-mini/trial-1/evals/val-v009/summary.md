# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 75.20

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.127 | 0.002 | 0.106 |
| summarize_hop1 | 1.315 | 1.224 | 1.968 |
| query_hop2 | 1.052 | 0.996 | 1.508 |
| retrieve_hop2 | 0.673 | 0.003 | 1.649 |
| summarize_hop2 | 1.300 | 1.260 | 1.763 |
| answer | 0.770 | 0.736 | 1.043 |
| **Total** | **5.237** | **4.701** | **7.281** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
