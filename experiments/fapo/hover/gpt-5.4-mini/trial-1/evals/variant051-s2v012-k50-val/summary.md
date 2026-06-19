# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.22
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.005 |
| summarize_hop1 | 2.510 | 2.331 | 3.978 |
| query_hop2 | 0.862 | 0.755 | 1.579 |
| retrieve_hop2 | 0.578 | 0.002 | 1.627 |
| summarize_hop2 | 3.905 | 3.307 | 7.160 |
| query_hop3 | 1.045 | 0.764 | 2.232 |
| retrieve_hop3 | 0.849 | 1.059 | 1.633 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.757** | **8.912** | **16.065** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 83 |
