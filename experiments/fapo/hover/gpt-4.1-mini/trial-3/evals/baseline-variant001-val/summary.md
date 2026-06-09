# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.00

## Score Breakdown
- num_found: 1.84
- num_gold: 3.00
- partial_recall: 61.33
- recall: 23.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.561 | 2.841 | 7.008 |
| query_hop2 | 1.032 | 0.788 | 2.103 |
| retrieve_hop2 | 1.491 | 1.392 | 1.655 |
| summarize_hop2 | 4.558 | 3.697 | 10.690 |
| query_hop3 | 1.204 | 0.892 | 2.045 |
| retrieve_hop3 | 1.149 | 1.332 | 1.651 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.998** | **11.446** | **24.900** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 231 |
