# Evaluation Summary

Total cases: 300

## Composite Score
- average: 80.00

## Score Breakdown
- num_found: 2.78
- num_gold: 3.00
- num_missing: 0.22
- partial_recall: 92.67
- recall: 80.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.316 | 2.886 | 6.400 |
| query_hop2 | 0.431 | 0.335 | 1.024 |
| retrieve_hop2 | 0.994 | 1.274 | 1.610 |
| summarize_hop2 | 7.108 | 6.005 | 10.850 |
| query_hop3 | 0.469 | 0.390 | 0.818 |
| retrieve_hop3 | 2.630 | 2.641 | 3.214 |
| summarize_hop3 | 7.136 | 6.963 | 12.395 |
| query_hop4 | 0.534 | 0.429 | 1.390 |
| retrieve_hop4 | 1.339 | 1.377 | 1.659 |
| query_hop5 | 0.578 | 0.492 | 1.098 |
| retrieve_hop5 | 2.244 | 2.577 | 3.147 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.783** | **25.839** | **34.400** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 60 |
