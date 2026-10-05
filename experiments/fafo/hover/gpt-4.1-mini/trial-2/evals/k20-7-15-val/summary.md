# Evaluation Summary

Total cases: 300

## Composite Score
- average: 27.33

## Score Breakdown
- num_found: 1.98
- num_gold: 3.00
- partial_recall: 66.00
- recall: 27.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 3.442 | 2.912 | 6.269 |
| query_hop2 | 0.722 | 0.540 | 1.296 |
| retrieve_hop2 | 0.281 | 0.002 | 1.588 |
| summarize_hop2 | 3.711 | 3.190 | 7.176 |
| query_hop3 | 0.780 | 0.564 | 1.336 |
| retrieve_hop3 | 1.232 | 1.535 | 1.681 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.172** | **9.178** | **17.420** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 218 |
