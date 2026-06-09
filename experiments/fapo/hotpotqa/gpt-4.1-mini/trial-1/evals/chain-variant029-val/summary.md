# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.009 |
| summarize_hop1 | 4.075 | 3.380 | 8.121 |
| query_hop2 | 1.958 | 1.708 | 3.201 |
| retrieve_hop2 | 0.428 | 0.002 | 1.570 |
| summarize_hop2 | 3.353 | 2.978 | 6.104 |
| answer | 2.235 | 1.922 | 4.473 |
| **Total** | **12.068** | **11.067** | **18.450** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
