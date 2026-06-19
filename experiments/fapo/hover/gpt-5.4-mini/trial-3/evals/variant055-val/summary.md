# Evaluation Summary

Total cases: 300

## Composite Score
- average: 55.67

## Score Breakdown
- num_found: 2.45
- num_gold: 3.00
- num_missing: 0.55
- partial_recall: 81.78
- recall: 55.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.012 |
| summarize_hop1 | 2.389 | 1.937 | 4.571 |
| query_hop2 | 0.886 | 0.758 | 1.299 |
| retrieve_hop2 | 1.631 | 1.560 | 1.662 |
| summarize_hop2 | 2.152 | 1.712 | 4.650 |
| query_hop3 | 0.893 | 0.762 | 1.182 |
| retrieve_hop3 | 1.475 | 1.543 | 1.661 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **9.430** | **8.685** | **15.224** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 133 |
