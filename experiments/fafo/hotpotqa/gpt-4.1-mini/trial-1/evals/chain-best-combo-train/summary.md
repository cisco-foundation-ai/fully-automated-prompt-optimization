# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.44

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.013 | 0.002 | 0.009 |
| summarize_hop1 | 3.796 | 3.240 | 6.704 |
| query_hop2 | 1.974 | 1.758 | 3.633 |
| retrieve_hop2 | 1.269 | 1.293 | 1.665 |
| summarize_hop2 | 2.912 | 2.686 | 4.722 |
| answer | 1.775 | 1.645 | 2.887 |
| **Total** | **11.739** | **10.881** | **18.802** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
