# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.71

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.126 | 0.002 | 0.105 |
| summarize_hop1 | 1.354 | 1.288 | 2.036 |
| query_hop2 | 1.170 | 1.046 | 1.776 |
| retrieve_hop2 | 0.472 | 0.002 | 1.588 |
| summarize_hop2 | 1.653 | 1.551 | 2.418 |
| answer | 0.805 | 0.738 | 1.297 |
| **Total** | **5.579** | **4.959** | **8.248** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
