# Evaluation Summary

Total cases: 150

## Composite Score
- average: 88.67

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- num_missing: 0.11
- partial_recall: 96.22
- recall: 88.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.643 | 5.211 | 9.776 |
| summarize_hop1 | 1.523 | 1.338 | 3.186 |
| retrieve_hop2 | 3.950 | 3.967 | 7.834 |
| summarize_hop2 | 1.391 | 1.180 | 2.854 |
| retrieve_hop3 | 2.442 | 1.622 | 6.364 |
| summarize_hop3 | 1.344 | 1.163 | 2.764 |
| retrieve_hop4 | 1.696 | 1.418 | 5.760 |
| summarize_hop4 | 1.293 | 1.122 | 2.345 |
| retrieve_hop5 | 1.570 | 1.373 | 4.088 |
| combine_retrievals | 0.026 | 0.024 | 0.051 |
| **Total** | **20.878** | **20.203** | **31.748** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5_trunc | 17 |
