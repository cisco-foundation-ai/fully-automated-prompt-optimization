# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.64
- num_gold: 3.00
- partial_recall: 88.11
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.010 | 0.024 |
| summarize_hop1 | 5.978 | 4.256 | 14.899 |
| query_hop2 | 0.946 | 0.823 | 1.687 |
| retrieve_hop2 | 21.691 | 19.482 | 46.540 |
| summarize_hop2 | 5.800 | 4.386 | 13.916 |
| query_hop3 | 1.154 | 0.962 | 2.100 |
| retrieve_hop3 | 19.391 | 18.121 | 37.563 |
| retrieve_mining | 16.799 | 16.096 | 26.981 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **71.774** | **69.654** | **108.392** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 83 |
