# Evaluation Summary

Total cases: 300

## Composite Score
- average: 84.33

## Score Breakdown
- num_found: 2.83
- num_gold: 3.00
- partial_recall: 94.22
- recall: 84.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.613 | 3.061 | 6.166 |
| query_hop2 | 1.110 | 0.865 | 1.572 |
| retrieve_hop2 | 0.851 | 0.003 | 1.586 |
| summarize_hop2 | 5.207 | 4.531 | 9.456 |
| query_hop3 | 1.561 | 1.093 | 3.565 |
| retrieve_hop3 | 0.336 | 0.002 | 1.546 |
| query_hop4 | 1.612 | 1.144 | 3.514 |
| retrieve_hop4 | 1.078 | 1.462 | 1.593 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **15.371** | **14.392** | **24.115** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 47 |
