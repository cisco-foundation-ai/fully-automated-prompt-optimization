# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- num_found: 2.55
- num_gold: 3.00
- partial_recall: 84.89
- recall: 62.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.004 |
| summarize_hop1 | 3.506 | 3.040 | 5.764 |
| query_hop2 | 0.955 | 0.569 | 1.913 |
| retrieve_hop2 | 1.409 | 1.286 | 1.548 |
| summarize_hop2 | 4.182 | 3.718 | 6.500 |
| query_hop3 | 0.775 | 0.593 | 1.641 |
| retrieve_hop3 | 0.581 | 0.003 | 1.525 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.410** | **10.285** | **17.769** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 112 |
