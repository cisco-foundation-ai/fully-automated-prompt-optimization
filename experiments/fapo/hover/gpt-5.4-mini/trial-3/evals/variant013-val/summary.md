# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.00

## Score Breakdown
- num_found: 1.84
- num_gold: 3.00
- num_missing: 1.16
- partial_recall: 61.22
- recall: 23.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.004 |
| summarize_hop1 | 1.955 | 1.742 | 2.678 |
| query_hop2 | 0.943 | 0.741 | 1.518 |
| retrieve_hop2 | 1.004 | 1.087 | 1.626 |
| summarize_hop2 | 1.876 | 1.823 | 2.551 |
| query_hop3 | 0.839 | 0.744 | 1.010 |
| retrieve_hop3 | 1.094 | 1.308 | 1.621 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.721** | **7.333** | **11.454** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 231 |
