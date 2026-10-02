# Evaluation Summary

Total cases: 150

## Composite Score
- average: 59.33

## Score Breakdown
- exact_match: 59.33
- f1: 66.71

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.368 | 1.196 | 1.749 |
| summarize_hop1 | 1.798 | 1.629 | 3.134 |
| query_hop2 | 1.023 | 0.968 | 1.647 |
| retrieve_hop2 | 1.292 | 1.539 | 1.689 |
| summarize_hop2 | 1.524 | 1.469 | 2.129 |
| answer | 0.909 | 0.859 | 1.336 |
| **Total** | **7.914** | **7.309** | **10.319** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 61 |
