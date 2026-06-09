# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.33

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.33
- recall: 74.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.011 |
| summarize_hop1 | 3.562 | 2.938 | 8.122 |
| query_hop2 | 0.415 | 0.331 | 1.121 |
| retrieve_hop2 | 0.377 | 0.005 | 1.577 |
| summarize_hop2 | 7.594 | 6.354 | 12.004 |
| query_hop3 | 0.431 | 0.351 | 0.813 |
| retrieve_hop3 | 0.964 | 1.269 | 1.639 |
| summarize_hop3 | 8.858 | 7.127 | 14.241 |
| query_hop4 | 0.540 | 0.453 | 1.143 |
| retrieve_hop4 | 1.344 | 1.361 | 1.668 |
| query_hop5 | 0.488 | 0.393 | 1.009 |
| retrieve_hop5 | 1.325 | 1.343 | 1.672 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.901** | **22.801** | **35.040** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 77 |
