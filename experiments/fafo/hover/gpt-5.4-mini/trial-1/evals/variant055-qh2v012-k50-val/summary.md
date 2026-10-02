# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.33

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- partial_recall: 90.44
- recall: 74.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.509 | 0.002 | 1.536 |
| summarize_hop1 | 2.720 | 2.444 | 4.388 |
| query_hop2 | 1.002 | 0.794 | 1.663 |
| retrieve_hop2 | 0.498 | 0.002 | 1.506 |
| summarize_hop2 | 3.876 | 3.478 | 6.133 |
| query_hop3 | 0.982 | 0.835 | 1.784 |
| retrieve_hop3 | 0.507 | 0.002 | 1.464 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.094** | **9.365** | **13.909** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 77 |
