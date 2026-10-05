# Evaluation Summary

Total cases: 300

## Composite Score
- average: 33.67

## Score Breakdown
- num_found: 2.12
- num_gold: 3.00
- num_missing: 0.88
- partial_recall: 70.67
- recall: 33.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 1.796 | 1.575 | 2.638 |
| query_hop2 | 0.818 | 0.664 | 1.024 |
| retrieve_hop2 | 1.332 | 1.314 | 1.649 |
| summarize_hop2 | 2.121 | 1.937 | 3.244 |
| query_hop3 | 0.768 | 0.684 | 1.099 |
| retrieve_hop3 | 1.417 | 1.316 | 1.660 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.255** | **7.728** | **11.461** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 199 |
