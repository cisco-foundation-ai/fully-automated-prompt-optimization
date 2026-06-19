# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- partial_recall: 89.56
- recall: 73.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.009 |
| summarize_hop1 | 2.380 | 2.118 | 3.616 |
| query_hop2 | 0.726 | 0.659 | 1.054 |
| retrieve_hop2 | 0.620 | 0.002 | 1.621 |
| summarize_hop2 | 3.507 | 3.059 | 5.704 |
| query_hop3 | 0.899 | 0.690 | 1.238 |
| retrieve_hop3 | 0.349 | 0.002 | 1.564 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.498** | **7.715** | **13.451** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 81 |
