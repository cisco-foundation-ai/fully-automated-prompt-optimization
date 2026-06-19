# Evaluation Summary

Total cases: 300

## Composite Score
- average: 31.00

## Score Breakdown
- num_found: 2.02
- num_gold: 3.00
- num_missing: 0.98
- partial_recall: 67.44
- recall: 31.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.002 | 0.524 | 1.693 |
| summarize_hop1 | 1.767 | 1.607 | 2.673 |
| query_hop2 | 0.804 | 0.700 | 1.013 |
| retrieve_hop2 | 1.364 | 1.320 | 1.596 |
| summarize_hop2 | 2.148 | 1.964 | 3.262 |
| query_hop3 | 0.880 | 0.706 | 1.206 |
| retrieve_hop3 | 1.387 | 1.336 | 1.610 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.351** | **8.717** | **12.221** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 207 |
