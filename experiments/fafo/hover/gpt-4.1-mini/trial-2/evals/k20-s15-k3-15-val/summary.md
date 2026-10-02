# Evaluation Summary

Total cases: 300

## Composite Score
- average: 29.00

## Score Breakdown
- num_found: 2.01
- num_gold: 3.00
- partial_recall: 66.89
- recall: 29.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 4.449 | 3.967 | 6.919 |
| query_hop2 | 0.646 | 0.555 | 1.032 |
| retrieve_hop2 | 0.225 | 0.002 | 1.396 |
| summarize_hop2 | 4.352 | 3.722 | 7.893 |
| query_hop3 | 0.839 | 0.587 | 1.484 |
| retrieve_hop3 | 1.181 | 1.245 | 1.522 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.695** | **10.495** | **18.614** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 213 |
