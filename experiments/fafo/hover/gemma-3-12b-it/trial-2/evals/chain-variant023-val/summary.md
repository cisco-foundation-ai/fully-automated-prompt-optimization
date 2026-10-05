# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.33

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.33
- recall: 76.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.009 |
| summarize_hop1 | 3.555 | 2.872 | 7.928 |
| query_hop2 | 0.399 | 0.331 | 0.682 |
| retrieve_hop2 | 0.379 | 0.002 | 1.486 |
| summarize_hop2 | 6.995 | 5.854 | 11.824 |
| query_hop3 | 0.453 | 0.358 | 1.155 |
| retrieve_hop3 | 1.017 | 1.232 | 1.562 |
| summarize_hop3 | 8.120 | 7.217 | 14.081 |
| query_hop4 | 0.523 | 0.449 | 0.813 |
| retrieve_hop4 | 1.273 | 1.320 | 1.573 |
| query_hop5 | 0.463 | 0.387 | 0.857 |
| retrieve_hop5 | 1.326 | 1.405 | 1.567 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.506** | **22.748** | **33.409** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 71 |
