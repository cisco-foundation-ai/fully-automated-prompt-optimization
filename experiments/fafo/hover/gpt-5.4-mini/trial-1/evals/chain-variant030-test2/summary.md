# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.33

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- partial_recall: 90.00
- recall: 75.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.005 |
| summarize_hop1 | 2.435 | 2.255 | 4.010 |
| query_hop2 | 0.810 | 0.711 | 1.087 |
| retrieve_hop2 | 1.114 | 1.088 | 1.675 |
| summarize_hop2 | 3.685 | 3.270 | 6.388 |
| query_hop3 | 0.839 | 0.772 | 1.442 |
| retrieve_hop3 | 0.736 | 1.038 | 1.655 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.627** | **9.183** | **13.462** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 74 |
