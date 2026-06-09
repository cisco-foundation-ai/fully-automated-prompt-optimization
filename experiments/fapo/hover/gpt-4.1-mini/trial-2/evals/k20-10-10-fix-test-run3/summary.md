# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.33

## Score Breakdown
- num_found: 2.52
- num_gold: 3.00
- partial_recall: 83.89
- recall: 59.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.004 |
| summarize_hop1 | 3.850 | 3.351 | 6.889 |
| query_hop2 | 0.911 | 0.599 | 1.691 |
| retrieve_hop2 | 0.275 | 0.002 | 1.496 |
| summarize_hop2 | 4.196 | 3.322 | 7.273 |
| query_hop3 | 0.908 | 0.615 | 1.562 |
| retrieve_hop3 | 0.812 | 1.211 | 1.527 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.965** | **9.346** | **19.275** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 122 |
