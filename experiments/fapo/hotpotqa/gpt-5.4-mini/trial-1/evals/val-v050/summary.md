# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- exact_match: 67.00
- f1: 75.23

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.233 | 0.881 | 1.694 |
| summarize_hop1 | 1.537 | 1.341 | 2.214 |
| query_hop2 | 1.214 | 1.108 | 1.706 |
| retrieve_hop2 | 1.233 | 1.285 | 1.608 |
| summarize_hop2 | 1.757 | 1.657 | 2.777 |
| answer | 1.005 | 0.765 | 1.999 |
| **Total** | **7.980** | **7.199** | **14.577** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 99 |
