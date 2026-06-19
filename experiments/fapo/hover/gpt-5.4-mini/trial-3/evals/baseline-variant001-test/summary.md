# Evaluation Summary

Total cases: 300

## Composite Score
- average: 25.67

## Score Breakdown
- num_found: 1.90
- num_gold: 3.00
- num_missing: 1.10
- partial_recall: 63.33
- recall: 25.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.115 | 1.123 | 1.665 |
| summarize_hop1 | 2.241 | 1.913 | 4.398 |
| query_hop2 | 1.624 | 1.260 | 2.971 |
| retrieve_hop2 | 0.896 | 1.128 | 1.655 |
| summarize_hop2 | 2.803 | 2.107 | 7.445 |
| query_hop3 | 2.528 | 1.185 | 3.358 |
| retrieve_hop3 | 1.092 | 1.298 | 1.654 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.299** | **10.145** | **19.572** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 223 |
