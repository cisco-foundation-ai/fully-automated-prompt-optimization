# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.00

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- partial_recall: 87.44
- recall: 67.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 2.531 | 2.143 | 3.712 |
| query_hop2 | 0.774 | 0.736 | 1.102 |
| retrieve_hop2 | 1.463 | 1.320 | 1.657 |
| summarize_hop2 | 2.013 | 1.706 | 2.823 |
| query_hop3 | 0.822 | 0.613 | 1.056 |
| retrieve_hop3 | 0.230 | 0.002 | 1.555 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.836** | **6.941** | **13.948** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 99 |
