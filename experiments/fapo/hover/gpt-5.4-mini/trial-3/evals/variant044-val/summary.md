# Evaluation Summary

Total cases: 300

## Composite Score
- average: 56.67

## Score Breakdown
- num_found: 2.52
- num_gold: 3.00
- num_missing: 0.48
- partial_recall: 83.89
- recall: 56.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.044 | 0.567 | 1.765 |
| summarize_hop1 | 3.059 | 2.611 | 5.297 |
| query_hop2 | 0.823 | 0.686 | 1.105 |
| retrieve_hop2 | 1.476 | 1.540 | 1.686 |
| summarize_hop2 | 3.229 | 2.832 | 5.844 |
| query_hop3 | 0.767 | 0.695 | 1.055 |
| retrieve_hop3 | 1.441 | 1.519 | 1.674 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **11.840** | **11.306** | **17.008** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 130 |
