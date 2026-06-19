# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 74.25

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.080 | 0.003 | 0.061 |
| summarize_hop1 | 2.525 | 2.386 | 4.393 |
| query_hop2 | 1.079 | 1.026 | 1.568 |
| retrieve_hop2 | 0.329 | 0.003 | 1.552 |
| summarize_hop2 | 2.736 | 2.582 | 4.573 |
| answer | 1.109 | 1.046 | 1.740 |
| **Total** | **7.859** | **7.238** | **11.563** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
