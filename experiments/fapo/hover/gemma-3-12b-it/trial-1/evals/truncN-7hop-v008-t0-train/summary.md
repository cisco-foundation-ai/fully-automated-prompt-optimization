# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 91.11
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.061 | 0.004 | 0.084 |
| summarize_hop1 | 4.409 | 3.867 | 10.720 |
| query_hop2 | 0.358 | 0.291 | 0.728 |
| retrieve_hop2 | 0.227 | 0.004 | 1.304 |
| summarize_hop2 | 3.210 | 2.551 | 7.746 |
| query_hop3 | 0.333 | 0.284 | 0.709 |
| retrieve_hop3 | 0.236 | 0.004 | 1.524 |
| summarize_hop3 | 2.556 | 1.973 | 5.697 |
| query_hop4 | 0.314 | 0.286 | 0.502 |
| retrieve_hop4 | 0.389 | 0.005 | 1.570 |
| summarize_hop4 | 2.427 | 1.946 | 5.374 |
| query_hop5 | 0.345 | 0.288 | 0.749 |
| retrieve_hop5 | 0.532 | 0.006 | 1.611 |
| summarize_hop5 | 2.266 | 1.820 | 4.653 |
| query_hop6 | 0.369 | 0.286 | 0.734 |
| retrieve_hop6 | 0.843 | 1.042 | 1.633 |
| summarize_hop6 | 4.961 | 1.722 | 5.843 |
| query_hop7 | 0.361 | 0.285 | 0.745 |
| retrieve_hop7 | 0.548 | 0.005 | 1.624 |
| combine_retrievals | 0.014 | 0.013 | 0.022 |
| **Total** | **24.760** | **21.761** | **39.459** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop7_trunc | 39 |
