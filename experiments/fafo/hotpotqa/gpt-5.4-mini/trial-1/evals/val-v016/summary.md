# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 73.81

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.137 | 0.002 | 0.121 |
| summarize_hop1 | 1.448 | 1.319 | 2.161 |
| query_hop2 | 1.122 | 1.046 | 1.678 |
| retrieve_hop2 | 0.549 | 0.002 | 1.673 |
| summarize_hop2 | 1.582 | 1.514 | 2.250 |
| answer | 0.866 | 0.796 | 1.415 |
| **Total** | **5.704** | **5.123** | **8.252** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
