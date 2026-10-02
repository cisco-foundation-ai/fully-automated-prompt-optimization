# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.00

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- partial_recall: 90.22
- recall: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.113 | 1.186 | 1.656 |
| summarize_hop1 | 2.843 | 2.506 | 4.572 |
| query_hop2 | 1.055 | 0.845 | 1.631 |
| retrieve_hop2 | 1.408 | 1.482 | 1.610 |
| summarize_hop2 | 4.159 | 3.518 | 7.922 |
| query_hop3 | 1.280 | 0.909 | 2.526 |
| retrieve_hop3 | 1.287 | 1.448 | 1.576 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.145** | **12.094** | **22.309** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 72 |
