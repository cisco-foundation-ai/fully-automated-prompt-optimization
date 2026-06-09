# Evaluation Summary

Total cases: 300

## Composite Score
- average: 81.00

## Score Breakdown
- num_found: 2.79
- num_gold: 3.00
- num_missing: 0.21
- partial_recall: 93.00
- recall: 81.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.622 | 2.961 | 7.965 |
| query_hop2 | 0.486 | 0.334 | 1.336 |
| retrieve_hop2 | 0.973 | 1.276 | 1.649 |
| summarize_hop2 | 6.925 | 6.188 | 12.639 |
| query_hop3 | 0.672 | 0.476 | 2.025 |
| retrieve_hop3 | 4.339 | 4.441 | 4.886 |
| summarize_hop3 | 7.131 | 6.760 | 12.436 |
| query_hop4 | 0.636 | 0.439 | 1.843 |
| retrieve_hop4 | 1.382 | 1.490 | 1.673 |
| query_hop5 | 0.651 | 0.471 | 1.637 |
| retrieve_hop5 | 2.186 | 2.501 | 3.209 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **29.007** | **28.595** | **38.794** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 57 |
