# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.19

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.139 | 0.002 | 0.119 |
| summarize_hop1 | 1.374 | 1.310 | 2.146 |
| query_hop2 | 1.098 | 1.018 | 1.525 |
| retrieve_hop2 | 0.465 | 0.002 | 1.586 |
| summarize_hop2 | 1.578 | 1.538 | 2.141 |
| answer | 0.813 | 0.752 | 1.224 |
| **Total** | **5.468** | **4.925** | **8.095** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
