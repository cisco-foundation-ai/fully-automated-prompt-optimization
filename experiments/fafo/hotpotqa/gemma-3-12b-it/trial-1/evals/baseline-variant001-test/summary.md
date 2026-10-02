# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.00

## Score Breakdown
- exact_match: 60.00
- f1: 66.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.008 |
| summarize_hop1 | 4.609 | 1.954 | 6.613 |
| query_hop2 | 4.224 | 1.200 | 4.663 |
| retrieve_hop2 | 1.560 | 1.546 | 1.662 |
| summarize_hop2 | 2.313 | 1.683 | 4.966 |
| answer | 4.617 | 1.059 | 4.706 |
| **Total** | **17.326** | **7.657** | **26.267** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 120 |
