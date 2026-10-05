# Evaluation Summary

Total cases: 300

## Composite Score
- average: 83.00

## Score Breakdown
- num_found: 2.82
- num_gold: 3.00
- partial_recall: 94.11
- recall: 83.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.003 | 0.007 |
| summarize_hop1 | 3.128 | 2.683 | 5.197 |
| query_hop2 | 0.954 | 0.817 | 1.591 |
| retrieve_hop2 | 0.658 | 0.006 | 1.561 |
| summarize_hop2 | 4.863 | 4.110 | 8.864 |
| query_hop3 | 1.527 | 0.960 | 3.597 |
| retrieve_hop3 | 0.334 | 0.005 | 1.502 |
| query_hop4 | 1.615 | 1.066 | 3.690 |
| retrieve_hop4 | 1.096 | 1.403 | 1.574 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **14.185** | **13.204** | **22.640** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 51 |
