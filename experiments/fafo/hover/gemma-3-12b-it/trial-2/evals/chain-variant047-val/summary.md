# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.00

## Score Breakdown
- num_found: 2.78
- num_gold: 3.00
- num_missing: 0.22
- partial_recall: 92.56
- recall: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.380 | 2.990 | 6.065 |
| query_hop2 | 0.405 | 0.333 | 0.718 |
| retrieve_hop2 | 0.687 | 0.018 | 1.613 |
| summarize_hop2 | 7.478 | 5.763 | 10.382 |
| query_hop3 | 0.561 | 0.460 | 0.971 |
| retrieve_hop3 | 3.643 | 3.790 | 4.823 |
| summarize_hop3 | 7.155 | 6.348 | 10.675 |
| query_hop4 | 0.530 | 0.423 | 1.006 |
| retrieve_hop4 | 1.337 | 1.379 | 1.665 |
| query_hop5 | 0.617 | 0.524 | 1.088 |
| retrieve_hop5 | 3.890 | 3.983 | 4.825 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **29.686** | **27.456** | **36.707** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 63 |
