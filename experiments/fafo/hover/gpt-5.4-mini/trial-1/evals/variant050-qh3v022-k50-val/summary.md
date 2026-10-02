# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.33

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- partial_recall: 90.11
- recall: 75.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.004 |
| summarize_hop1 | 2.540 | 2.349 | 4.158 |
| query_hop2 | 0.907 | 0.760 | 1.429 |
| retrieve_hop2 | 0.458 | 0.002 | 1.573 |
| summarize_hop2 | 3.873 | 3.405 | 7.216 |
| query_hop3 | 1.284 | 0.864 | 1.914 |
| retrieve_hop3 | 1.498 | 1.491 | 1.633 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.563** | **9.634** | **15.185** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 74 |
