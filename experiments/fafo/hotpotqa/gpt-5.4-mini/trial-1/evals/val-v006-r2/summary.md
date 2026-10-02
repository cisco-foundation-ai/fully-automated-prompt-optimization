# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.12

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.108 | 0.002 | 0.114 |
| summarize_hop1 | 1.186 | 1.096 | 1.884 |
| query_hop2 | 1.279 | 1.042 | 1.534 |
| retrieve_hop2 | 0.805 | 0.003 | 1.699 |
| summarize_hop2 | 1.120 | 1.022 | 1.549 |
| answer | 0.882 | 0.749 | 1.375 |
| **Total** | **5.380** | **4.618** | **9.579** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
