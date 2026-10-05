# Evaluation Summary

Total cases: 300

## Composite Score
- average: 32.00

## Score Breakdown
- num_found: 2.08
- num_gold: 3.00
- num_missing: 0.92
- partial_recall: 69.22
- recall: 32.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.009 |
| summarize_hop1 | 2.096 | 1.720 | 2.757 |
| query_hop2 | 1.022 | 0.950 | 1.535 |
| retrieve_hop2 | 1.176 | 1.133 | 1.693 |
| summarize_hop2 | 2.279 | 1.954 | 3.380 |
| query_hop3 | 1.064 | 0.864 | 1.519 |
| retrieve_hop3 | 1.111 | 1.341 | 1.667 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.753** | **7.946** | **16.720** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 204 |
