# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.67

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.44
- recall: 73.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.010 |
| summarize_hop1 | 3.337 | 2.683 | 7.137 |
| query_hop2 | 0.374 | 0.317 | 0.575 |
| retrieve_hop2 | 0.349 | 0.002 | 1.499 |
| summarize_hop2 | 6.854 | 5.903 | 10.490 |
| query_hop3 | 0.397 | 0.332 | 0.702 |
| retrieve_hop3 | 0.891 | 1.268 | 1.574 |
| summarize_hop3 | 9.130 | 7.079 | 12.460 |
| query_hop4 | 0.477 | 0.431 | 0.810 |
| retrieve_hop4 | 1.331 | 1.446 | 1.607 |
| query_hop5 | 0.435 | 0.376 | 0.848 |
| retrieve_hop5 | 1.340 | 1.456 | 1.586 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.920** | **21.822** | **31.305** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 79 |
