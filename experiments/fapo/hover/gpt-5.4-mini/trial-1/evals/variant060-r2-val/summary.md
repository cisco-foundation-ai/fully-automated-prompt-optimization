# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.33

## Score Breakdown
- num_found: 2.75
- num_gold: 3.00
- partial_recall: 91.67
- recall: 77.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.006 |
| summarize_hop1 | 2.741 | 2.333 | 3.986 |
| query_hop2 | 0.927 | 0.773 | 1.679 |
| retrieve_hop2 | 0.919 | 1.058 | 1.565 |
| summarize_hop2 | 3.869 | 3.438 | 7.206 |
| query_hop3 | 0.930 | 0.840 | 1.559 |
| retrieve_hop3 | 0.374 | 0.002 | 1.532 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.777** | **8.832** | **14.973** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 68 |
