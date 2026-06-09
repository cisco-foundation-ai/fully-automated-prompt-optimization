# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- num_found: 2.59
- num_gold: 3.00
- partial_recall: 86.33
- recall: 65.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.005 |
| summarize_hop1 | 4.913 | 4.223 | 8.557 |
| query_hop2 | 0.756 | 0.593 | 1.646 |
| retrieve_hop2 | 0.846 | 1.206 | 1.533 |
| summarize_hop2 | 4.544 | 4.095 | 8.071 |
| query_hop3 | 0.732 | 0.619 | 1.245 |
| retrieve_hop3 | 0.764 | 0.897 | 1.528 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.564** | **11.903** | **18.593** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 103 |
