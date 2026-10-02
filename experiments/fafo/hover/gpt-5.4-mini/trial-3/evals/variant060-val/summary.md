# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- num_missing: 0.37
- partial_recall: 87.78
- recall: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.972 | 0.573 | 1.665 |
| summarize_hop1 | 5.174 | 4.825 | 7.608 |
| query_hop2 | 0.908 | 0.771 | 1.241 |
| retrieve_hop2 | 1.201 | 1.294 | 1.614 |
| summarize_hop2 | 2.859 | 2.609 | 5.398 |
| query_hop3 | 0.997 | 0.756 | 1.518 |
| retrieve_hop3 | 1.156 | 1.296 | 1.602 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.267** | **12.756** | **18.257** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 100 |
