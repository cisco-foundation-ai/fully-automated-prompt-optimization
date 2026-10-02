# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.00

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.33
- recall: 75.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.897 | 0.433 | 1.542 |
| summarize_hop1 | 3.873 | 2.723 | 7.141 |
| query_hop2 | 0.375 | 0.317 | 0.694 |
| retrieve_hop2 | 0.279 | 0.002 | 1.418 |
| summarize_hop2 | 6.862 | 5.969 | 9.789 |
| query_hop3 | 0.401 | 0.328 | 0.678 |
| retrieve_hop3 | 0.747 | 1.043 | 1.467 |
| summarize_hop3 | 8.800 | 6.514 | 13.334 |
| query_hop4 | 0.484 | 0.428 | 0.896 |
| retrieve_hop4 | 1.139 | 1.093 | 1.529 |
| query_hop5 | 0.404 | 0.356 | 0.687 |
| retrieve_hop5 | 1.185 | 1.081 | 1.518 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.447** | **21.810** | **32.442** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 75 |
