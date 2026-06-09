# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.44
- recall: 73.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.004 |
| summarize_hop1 | 2.324 | 2.215 | 3.426 |
| query_hop2 | 0.861 | 0.726 | 1.105 |
| retrieve_hop2 | 1.068 | 1.344 | 1.657 |
| summarize_hop2 | 1.869 | 1.734 | 2.866 |
| query_hop3 | 0.804 | 0.605 | 1.065 |
| retrieve_hop3 | 0.179 | 0.002 | 1.561 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.119** | **6.747** | **10.662** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 81 |
