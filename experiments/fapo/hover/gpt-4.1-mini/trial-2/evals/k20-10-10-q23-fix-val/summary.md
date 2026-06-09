# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- partial_recall: 87.00
- recall: 67.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.005 |
| summarize_hop1 | 5.634 | 4.331 | 10.069 |
| query_hop2 | 0.921 | 0.595 | 1.548 |
| retrieve_hop2 | 0.336 | 0.002 | 1.278 |
| summarize_hop2 | 4.928 | 4.229 | 8.094 |
| query_hop3 | 0.828 | 0.609 | 1.900 |
| retrieve_hop3 | 0.370 | 0.003 | 1.308 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.025** | **11.167** | **24.982** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 98 |
