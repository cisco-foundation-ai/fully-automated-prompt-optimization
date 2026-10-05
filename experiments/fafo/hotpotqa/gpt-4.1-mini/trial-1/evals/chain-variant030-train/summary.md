# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 80.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.014 |
| summarize_hop1 | 3.062 | 2.706 | 6.131 |
| query_hop2 | 2.065 | 1.809 | 3.937 |
| retrieve_hop2 | 0.519 | 0.002 | 1.591 |
| summarize_hop2 | 3.143 | 2.860 | 5.408 |
| answer | 1.819 | 1.598 | 3.536 |
| **Total** | **10.623** | **9.957** | **16.338** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
