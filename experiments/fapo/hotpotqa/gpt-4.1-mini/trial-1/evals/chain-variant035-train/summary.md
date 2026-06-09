# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.08

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.063 | 0.002 | 0.038 |
| summarize_hop1 | 3.437 | 2.901 | 6.592 |
| query_hop2 | 2.040 | 1.761 | 3.827 |
| retrieve_hop2 | 0.481 | 0.002 | 1.607 |
| summarize_hop2 | 3.799 | 3.050 | 6.898 |
| answer | 2.120 | 1.786 | 4.347 |
| **Total** | **11.939** | **11.306** | **19.608** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
| query_hop2 | 1 |
