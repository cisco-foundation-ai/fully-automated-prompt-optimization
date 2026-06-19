# Evaluation Summary

Total cases: 150

## Composite Score
- average: 84.67

## Score Breakdown
- num_found: 2.85
- num_gold: 3.00
- num_missing: 0.15
- partial_recall: 94.89
- recall: 84.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 3.857 | 3.971 | 8.518 |
| summarize_hop1 | 1.291 | 1.100 | 2.402 |
| retrieve_hop2 | 3.434 | 3.037 | 7.953 |
| summarize_hop2 | 1.265 | 1.123 | 2.211 |
| retrieve_hop3 | 2.513 | 1.657 | 6.499 |
| combine_retrievals | 0.015 | 0.014 | 0.031 |
| **Total** | **12.377** | **11.922** | **23.079** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 23 |
