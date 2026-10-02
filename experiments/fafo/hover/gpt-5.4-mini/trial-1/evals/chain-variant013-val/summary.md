# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- partial_recall: 89.56
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.006 |
| summarize_hop1 | 2.425 | 2.213 | 3.822 |
| query_hop2 | 0.841 | 0.756 | 1.335 |
| retrieve_hop2 | 1.406 | 1.368 | 1.693 |
| summarize_hop2 | 2.011 | 1.860 | 2.853 |
| query_hop3 | 0.949 | 0.715 | 1.544 |
| retrieve_hop3 | 0.544 | 0.002 | 1.641 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.187** | **7.755** | **11.524** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 83 |
