# Evaluation Summary

Total cases: 300

## Composite Score
- average: 61.33

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- num_missing: 0.43
- partial_recall: 85.56
- recall: 61.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.056 | 0.571 | 1.736 |
| summarize_hop1 | 3.954 | 3.660 | 6.609 |
| query_hop2 | 0.991 | 0.753 | 1.226 |
| retrieve_hop2 | 1.413 | 1.532 | 1.670 |
| summarize_hop2 | 3.111 | 2.657 | 6.105 |
| query_hop3 | 0.894 | 0.746 | 1.177 |
| retrieve_hop3 | 1.422 | 1.534 | 1.675 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.841** | **12.159** | **19.132** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 116 |
