# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.78
- recall: 74.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.007 |
| summarize_hop1 | 3.688 | 2.950 | 7.864 |
| query_hop2 | 0.423 | 0.326 | 0.890 |
| retrieve_hop2 | 1.493 | 1.447 | 1.633 |
| summarize_hop2 | 5.432 | 5.098 | 9.945 |
| query_hop3 | 0.489 | 0.337 | 1.566 |
| retrieve_hop3 | 1.392 | 1.482 | 1.630 |
| summarize_hop3 | 6.420 | 5.872 | 11.870 |
| query_hop4 | 0.569 | 0.432 | 1.160 |
| retrieve_hop4 | 1.414 | 1.514 | 1.660 |
| query_hop5 | 0.632 | 0.502 | 1.706 |
| retrieve_hop5 | 2.646 | 2.878 | 3.226 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.603** | **23.742** | **34.131** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 77 |
