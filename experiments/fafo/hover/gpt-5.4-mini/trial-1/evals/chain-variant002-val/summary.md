# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.78
- recall: 65.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 2.193 | 2.059 | 3.340 |
| query_hop2 | 0.901 | 0.775 | 1.484 |
| retrieve_hop2 | 1.543 | 1.497 | 1.664 |
| summarize_hop2 | 2.408 | 2.109 | 3.897 |
| query_hop3 | 0.893 | 0.760 | 1.475 |
| retrieve_hop3 | 1.353 | 1.500 | 1.658 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.295** | **8.725** | **12.524** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 103 |
