# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.06

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.059 | 0.003 | 0.042 |
| summarize_hop1 | 2.959 | 2.445 | 6.192 |
| query_hop2 | 1.528 | 1.450 | 2.333 |
| retrieve_hop2 | 0.572 | 0.002 | 1.648 |
| summarize_hop2 | 2.708 | 2.494 | 4.347 |
| answer | 1.582 | 1.423 | 2.820 |
| **Total** | **9.407** | **8.955** | **15.666** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
