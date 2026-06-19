# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.008 |
| summarize_hop1 | 1.344 | 1.248 | 1.992 |
| query_hop2 | 1.167 | 1.064 | 1.572 |
| retrieve_hop2 | 1.531 | 1.355 | 1.731 |
| summarize_hop2 | 1.405 | 1.344 | 1.990 |
| answer | 0.882 | 0.798 | 1.275 |
| **Total** | **6.332** | **5.822** | **10.253** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
