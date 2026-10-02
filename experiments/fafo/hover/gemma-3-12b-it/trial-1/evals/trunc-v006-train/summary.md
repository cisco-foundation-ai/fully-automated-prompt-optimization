# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- num_missing: 0.33
- partial_recall: 89.11
- recall: 68.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.565 | 0.135 | 1.719 |
| summarize_hop1 | 2.663 | 2.045 | 5.684 |
| query_hop2 | 0.319 | 0.290 | 0.480 |
| retrieve_hop2 | 1.669 | 1.567 | 1.671 |
| summarize_hop2 | 1.914 | 1.635 | 3.925 |
| query_hop3 | 0.304 | 0.277 | 0.456 |
| retrieve_hop3 | 1.173 | 1.413 | 1.657 |
| combine_retrievals | 0.005 | 0.005 | 0.008 |
| **Total** | **8.611** | **7.550** | **19.023** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 47 |
