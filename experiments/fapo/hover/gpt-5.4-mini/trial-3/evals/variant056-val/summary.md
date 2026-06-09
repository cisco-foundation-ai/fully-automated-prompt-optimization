# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.00

## Score Breakdown
- num_found: 2.49
- num_gold: 3.00
- num_missing: 0.51
- partial_recall: 83.11
- recall: 57.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.006 |
| summarize_hop1 | 3.098 | 2.761 | 5.645 |
| query_hop2 | 1.006 | 0.792 | 1.350 |
| retrieve_hop2 | 1.535 | 1.348 | 1.702 |
| summarize_hop2 | 3.762 | 3.175 | 7.317 |
| query_hop3 | 0.950 | 0.808 | 1.318 |
| retrieve_hop3 | 1.287 | 1.333 | 1.683 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **11.644** | **10.726** | **17.735** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 129 |
