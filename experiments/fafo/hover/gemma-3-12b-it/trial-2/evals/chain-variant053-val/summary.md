# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.67

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.44
- recall: 79.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.255 | 2.909 | 6.111 |
| query_hop2 | 0.397 | 0.325 | 0.870 |
| retrieve_hop2 | 0.480 | 0.002 | 1.505 |
| summarize_hop2 | 6.659 | 6.197 | 10.614 |
| query_hop3 | 0.514 | 0.378 | 1.164 |
| retrieve_hop3 | 1.343 | 1.246 | 3.039 |
| summarize_hop3 | 7.250 | 6.396 | 11.578 |
| query_hop4 | 0.519 | 0.417 | 1.061 |
| retrieve_hop4 | 2.302 | 2.481 | 3.118 |
| query_hop5 | 0.674 | 0.465 | 1.800 |
| retrieve_hop5 | 1.798 | 1.562 | 3.056 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.193** | **24.046** | **33.347** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 61 |
