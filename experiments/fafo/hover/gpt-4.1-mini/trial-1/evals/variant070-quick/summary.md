# Evaluation Summary

Total cases: 75

## Composite Score
- average: 52.00

## Score Breakdown
- num_found: 2.44
- num_gold: 3.00
- partial_recall: 81.33
- recall: 52.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.579 | 1.277 | 3.120 |
| summarize_hop1 | 4.336 | 3.668 | 9.886 |
| query_hop2 | 0.773 | 0.689 | 1.272 |
| retrieve_hop2 | 1.662 | 1.395 | 3.297 |
| summarize_hop2 | 4.658 | 3.357 | 10.388 |
| query_hop3 | 0.903 | 0.753 | 1.764 |
| retrieve_hop3 | 5.968 | 4.994 | 12.667 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **19.878** | **18.585** | **32.559** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 36 |
