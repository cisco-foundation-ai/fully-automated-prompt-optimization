# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.022 |
| summarize_hop1 | 2.348 | 2.179 | 4.120 |
| query_hop2 | 1.271 | 1.219 | 1.790 |
| retrieve_hop2 | 0.693 | 0.002 | 1.675 |
| summarize_hop2 | 1.809 | 1.698 | 2.618 |
| answer | 0.979 | 0.953 | 1.378 |
| **Total** | **7.134** | **6.466** | **10.365** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
