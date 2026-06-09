# Evaluation Summary

Total cases: 300

## Composite Score
- average: 98.67

## Score Breakdown
- num_found: 2.99
- num_gold: 3.00
- partial_recall: 99.56
- recall: 98.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.938 | 0.512 | 1.573 |
| summarize_hop1 | 35.464 | 28.660 | 74.376 |
| query_hop2 | 1.463 | 1.244 | 2.174 |
| retrieve_hop2 | 9.365 | 9.863 | 11.765 |
| summarize_hop2 | 33.061 | 28.194 | 55.187 |
| query_hop3 | 2.071 | 1.339 | 6.299 |
| retrieve_hop3 | 7.933 | 7.961 | 10.563 |
| summarize_hop3 | 33.862 | 27.577 | 61.265 |
| query_hop4 | 1.855 | 1.511 | 3.031 |
| retrieve_hop4 | 9.140 | 9.075 | 12.950 |
| summarize_hop4 | 43.261 | 35.702 | 77.161 |
| query_hop5 | 3.893 | 2.567 | 10.711 |
| retrieve_hop5 | 15.470 | 15.366 | 21.071 |
| combine_retrievals | 0.011 | 0.010 | 0.021 |
| **Total** | **197.788** | **181.183** | **283.641** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 4 |
