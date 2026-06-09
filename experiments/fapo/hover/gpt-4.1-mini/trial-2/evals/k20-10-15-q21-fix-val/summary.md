# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- partial_recall: 86.89
- recall: 66.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.004 |
| summarize_hop1 | 5.238 | 4.290 | 10.925 |
| query_hop2 | 0.933 | 0.613 | 2.255 |
| retrieve_hop2 | 0.174 | 0.002 | 1.449 |
| summarize_hop2 | 5.329 | 4.587 | 10.897 |
| query_hop3 | 0.874 | 0.632 | 2.071 |
| retrieve_hop3 | 1.041 | 1.250 | 1.574 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.603** | **12.313** | **24.092** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 101 |
