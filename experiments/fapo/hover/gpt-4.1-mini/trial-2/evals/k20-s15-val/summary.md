# Evaluation Summary

Total cases: 300

## Composite Score
- average: 29.67

## Score Breakdown
- num_found: 2.02
- num_gold: 3.00
- partial_recall: 67.44
- recall: 29.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.007 |
| summarize_hop1 | 4.183 | 3.498 | 6.209 |
| query_hop2 | 0.736 | 0.562 | 1.198 |
| retrieve_hop2 | 0.319 | 0.002 | 1.532 |
| summarize_hop2 | 4.075 | 3.514 | 7.142 |
| query_hop3 | 0.775 | 0.596 | 1.611 |
| retrieve_hop3 | 0.577 | 0.002 | 1.555 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.683** | **9.409** | **17.106** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 211 |
