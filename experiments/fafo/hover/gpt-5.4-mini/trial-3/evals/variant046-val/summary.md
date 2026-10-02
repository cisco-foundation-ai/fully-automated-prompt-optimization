# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- num_found: 2.52
- num_gold: 3.00
- num_missing: 0.48
- partial_recall: 84.00
- recall: 58.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.008 |
| summarize_hop1 | 2.888 | 2.356 | 5.442 |
| query_hop2 | 0.827 | 0.706 | 1.214 |
| retrieve_hop2 | 1.396 | 1.334 | 1.665 |
| summarize_hop2 | 3.467 | 3.010 | 6.308 |
| query_hop3 | 0.852 | 0.726 | 1.077 |
| retrieve_hop3 | 1.404 | 1.344 | 1.650 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **10.839** | **10.268** | **16.855** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 125 |
