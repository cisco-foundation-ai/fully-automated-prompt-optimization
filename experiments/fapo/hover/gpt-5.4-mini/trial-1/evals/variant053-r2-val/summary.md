# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.67

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- partial_recall: 91.89
- recall: 78.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.009 |
| summarize_hop1 | 2.945 | 2.720 | 4.819 |
| query_hop2 | 1.003 | 0.824 | 1.835 |
| retrieve_hop2 | 1.220 | 1.254 | 1.562 |
| summarize_hop2 | 4.418 | 3.947 | 8.035 |
| query_hop3 | 1.207 | 0.964 | 2.663 |
| retrieve_hop3 | 0.591 | 0.003 | 1.510 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.394** | **10.831** | **16.937** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 64 |
