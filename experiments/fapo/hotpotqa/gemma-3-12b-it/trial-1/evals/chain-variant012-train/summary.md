# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.044 | 0.003 | 0.021 |
| summarize_hop1 | 2.271 | 2.185 | 3.808 |
| query_hop2 | 1.260 | 1.202 | 1.744 |
| retrieve_hop2 | 0.708 | 0.006 | 1.353 |
| summarize_hop2 | 2.666 | 2.146 | 3.656 |
| answer | 1.082 | 1.006 | 1.347 |
| **Total** | **8.031** | **6.922** | **12.239** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
