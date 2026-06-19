# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.22
- recall: 72.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.006 | 0.004 | 0.007 |
| summarize_hop1 | 6.278 | 5.722 | 12.622 |
| query_hop2 | 0.320 | 0.296 | 0.514 |
| retrieve_hop2 | 1.390 | 1.264 | 1.648 |
| summarize_hop2 | 11.378 | 3.154 | 15.416 |
| query_hop3 | 0.386 | 0.292 | 1.214 |
| retrieve_hop3 | 1.110 | 1.257 | 1.628 |
| summarize_hop3 | 11.157 | 2.242 | 14.373 |
| query_hop4 | 0.370 | 0.293 | 0.786 |
| retrieve_hop4 | 1.034 | 1.247 | 1.656 |
| summarize_hop4 | 8.868 | 1.870 | 8.546 |
| query_hop5 | 0.363 | 0.288 | 0.775 |
| retrieve_hop5 | 0.821 | 1.055 | 1.626 |
| combine_retrievals | 0.009 | 0.009 | 0.015 |
| **Total** | **43.489** | **20.671** | **240.393** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5_trunc | 42 |
