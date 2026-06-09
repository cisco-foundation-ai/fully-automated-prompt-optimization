# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- num_found: 2.59
- num_gold: 3.00
- partial_recall: 86.22
- recall: 66.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.009 |
| summarize_hop1 | 2.263 | 2.042 | 3.605 |
| query_hop2 | 0.769 | 0.668 | 1.147 |
| retrieve_hop2 | 0.652 | 0.002 | 1.596 |
| summarize_hop2 | 1.883 | 1.800 | 2.575 |
| query_hop3 | 0.748 | 0.626 | 0.946 |
| retrieve_hop3 | 0.349 | 0.002 | 1.562 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **6.673** | **6.046** | **9.818** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 101 |
