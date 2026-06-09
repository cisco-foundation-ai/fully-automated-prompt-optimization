# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- partial_recall: 88.33
- recall: 69.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.009 |
| summarize_hop1 | 2.311 | 2.125 | 3.644 |
| query_hop2 | 0.724 | 0.664 | 0.979 |
| retrieve_hop2 | 0.844 | 1.045 | 1.654 |
| summarize_hop2 | 1.073 | 0.988 | 1.515 |
| query_hop3 | 0.653 | 0.558 | 0.920 |
| retrieve_hop3 | 0.834 | 1.058 | 1.621 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **6.455** | **6.049** | **9.129** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 92 |
| query_hop3 | 1 |
