# Evaluation Summary

Total cases: 300

## Composite Score
- average: 81.00

## Score Breakdown
- num_found: 2.79
- num_gold: 3.00
- num_missing: 0.21
- partial_recall: 93.00
- recall: 81.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.171 | 2.734 | 5.988 |
| query_hop2 | 0.397 | 0.331 | 0.705 |
| retrieve_hop2 | 0.642 | 0.002 | 1.531 |
| summarize_hop2 | 6.518 | 5.923 | 10.412 |
| query_hop3 | 0.470 | 0.378 | 1.037 |
| retrieve_hop3 | 1.364 | 1.317 | 2.993 |
| summarize_hop3 | 8.384 | 6.400 | 11.304 |
| query_hop4 | 0.508 | 0.423 | 0.986 |
| retrieve_hop4 | 1.338 | 1.361 | 1.621 |
| summarize_hop4 | 14.646 | 12.217 | 18.829 |
| query_hop5 | 0.547 | 0.471 | 0.870 |
| retrieve_hop5 | 1.964 | 1.619 | 3.031 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **39.952** | **35.725** | **49.861** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 57 |
