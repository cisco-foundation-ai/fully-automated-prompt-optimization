# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.33
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.442 | 5.044 | 9.356 |
| summarize_hop1 | 3.486 | 2.873 | 6.955 |
| query_hop2 | 0.304 | 0.278 | 0.445 |
| retrieve_hop2 | 6.265 | 6.460 | 7.923 |
| summarize_hop2 | 2.583 | 2.142 | 5.592 |
| query_hop3 | 0.344 | 0.285 | 0.609 |
| retrieve_hop3 | 6.507 | 6.556 | 7.926 |
| combine_retrievals | 0.026 | 0.024 | 0.042 |
| **Total** | **24.957** | **24.187** | **33.212** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 38 |
