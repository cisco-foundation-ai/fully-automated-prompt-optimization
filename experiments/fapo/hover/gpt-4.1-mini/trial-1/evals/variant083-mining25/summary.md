# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- partial_recall: 87.11
- recall: 68.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.010 | 0.023 |
| summarize_hop1 | 7.118 | 4.804 | 17.300 |
| query_hop2 | 1.249 | 0.885 | 2.491 |
| retrieve_hop2 | 6.783 | 3.414 | 27.074 |
| summarize_hop2 | 6.703 | 5.168 | 16.697 |
| query_hop3 | 1.218 | 1.042 | 2.249 |
| retrieve_hop3 | 15.183 | 13.687 | 30.870 |
| retrieve_mining | 6.148 | 5.360 | 13.052 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **44.418** | **43.005** | **76.831** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 94 |
