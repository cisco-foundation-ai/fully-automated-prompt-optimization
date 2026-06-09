# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- partial_recall: 89.11
- recall: 70.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.003 |
| summarize_hop1 | 2.426 | 2.183 | 4.054 |
| query_hop2 | 0.977 | 0.726 | 1.499 |
| retrieve_hop2 | 1.251 | 1.514 | 1.660 |
| summarize_hop2 | 1.959 | 1.796 | 2.833 |
| query_hop3 | 0.664 | 0.580 | 0.882 |
| retrieve_hop3 | 0.151 | 0.002 | 1.530 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.437** | **6.768** | **10.447** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 88 |
