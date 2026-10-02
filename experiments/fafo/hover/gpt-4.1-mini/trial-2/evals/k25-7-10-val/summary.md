# Evaluation Summary

Total cases: 300

## Composite Score
- average: 27.67

## Score Breakdown
- num_found: 2.01
- num_gold: 3.00
- partial_recall: 67.11
- recall: 27.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.007 | 0.002 | 0.009 |
| summarize_hop1 | 4.674 | 4.059 | 8.781 |
| query_hop2 | 0.915 | 0.575 | 1.371 |
| retrieve_hop2 | 0.277 | 0.002 | 1.121 |
| summarize_hop2 | 4.992 | 4.333 | 9.706 |
| query_hop3 | 0.909 | 0.585 | 2.152 |
| retrieve_hop3 | 0.489 | 0.002 | 1.528 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.263** | **10.971** | **21.939** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 217 |
