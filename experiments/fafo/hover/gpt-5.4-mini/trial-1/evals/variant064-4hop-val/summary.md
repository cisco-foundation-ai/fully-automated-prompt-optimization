# Evaluation Summary

Total cases: 300

## Composite Score
- average: 84.00

## Score Breakdown
- num_found: 2.81
- num_gold: 3.00
- partial_recall: 93.78
- recall: 84.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.005 |
| summarize_hop1 | 2.612 | 2.466 | 4.028 |
| query_hop2 | 1.056 | 0.841 | 1.562 |
| retrieve_hop2 | 0.769 | 0.798 | 1.555 |
| summarize_hop2 | 4.582 | 3.545 | 7.197 |
| query_hop3 | 1.164 | 0.907 | 2.066 |
| retrieve_hop3 | 0.306 | 0.002 | 1.507 |
| query_hop4 | 1.344 | 0.994 | 2.563 |
| retrieve_hop4 | 1.174 | 1.263 | 1.564 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.016** | **11.822** | **20.526** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 48 |
