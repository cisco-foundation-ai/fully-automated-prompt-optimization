# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- exact_match: 66.33
- f1: 74.63

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.008 |
| summarize_hop1 | 3.423 | 2.971 | 6.789 |
| query_hop2 | 1.768 | 1.539 | 2.970 |
| retrieve_hop2 | 0.554 | 0.002 | 1.613 |
| summarize_hop2 | 3.117 | 2.875 | 5.243 |
| answer | 1.464 | 1.300 | 2.363 |
| **Total** | **10.353** | **9.639** | **16.524** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 101 |
