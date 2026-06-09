# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- num_found: 2.47
- num_gold: 3.00
- partial_recall: 82.33
- recall: 58.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.007 |
| summarize_hop1 | 2.435 | 1.966 | 4.127 |
| query_hop2 | 0.845 | 0.547 | 1.026 |
| retrieve_hop2 | 0.371 | 0.002 | 1.524 |
| summarize_hop2 | 3.351 | 2.466 | 4.516 |
| query_hop3 | 0.731 | 0.581 | 1.320 |
| retrieve_hop3 | 0.914 | 1.075 | 1.581 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.661** | **7.130** | **15.290** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 125 |
