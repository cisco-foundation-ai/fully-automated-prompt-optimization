# Evaluation Summary

Total cases: 300

## Composite Score
- average: 47.00

## Score Breakdown
- num_found: 2.23
- num_gold: 3.00
- num_missing: 0.77
- partial_recall: 74.33
- recall: 47.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.081 | 1.110 | 1.661 |
| summarize_hop1 | 4.086 | 2.311 | 3.875 |
| query_hop2 | 4.186 | 3.208 | 6.100 |
| retrieve_hop2 | 0.190 | 0.098 | 1.193 |
| summarize_hop2 | 2.710 | 2.635 | 4.331 |
| query_hop3 | 3.997 | 2.567 | 4.634 |
| retrieve_hop3 | 0.222 | 0.095 | 1.323 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **16.472** | **12.316** | **18.994** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 159 |
