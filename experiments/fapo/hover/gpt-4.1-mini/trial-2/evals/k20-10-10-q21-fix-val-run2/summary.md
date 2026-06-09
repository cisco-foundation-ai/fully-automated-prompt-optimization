# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.00

## Score Breakdown
- num_found: 2.60
- num_gold: 3.00
- partial_recall: 86.67
- recall: 66.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.002 | 0.006 |
| summarize_hop1 | 3.358 | 3.077 | 5.200 |
| query_hop2 | 0.713 | 0.580 | 1.292 |
| retrieve_hop2 | 0.309 | 0.002 | 1.461 |
| summarize_hop2 | 3.587 | 3.147 | 5.347 |
| query_hop3 | 0.678 | 0.587 | 1.369 |
| retrieve_hop3 | 0.538 | 0.002 | 1.483 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.207** | **8.450** | **14.080** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 102 |
