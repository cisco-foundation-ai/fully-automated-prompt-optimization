# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.67

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- partial_recall: 90.89
- recall: 76.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.006 |
| summarize_hop1 | 2.347 | 2.175 | 3.684 |
| query_hop2 | 0.817 | 0.661 | 1.262 |
| retrieve_hop2 | 0.659 | 0.002 | 1.671 |
| summarize_hop2 | 3.343 | 3.003 | 5.965 |
| query_hop3 | 0.810 | 0.698 | 1.335 |
| retrieve_hop3 | 0.539 | 0.002 | 1.661 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.543** | **7.959** | **12.712** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 70 |
