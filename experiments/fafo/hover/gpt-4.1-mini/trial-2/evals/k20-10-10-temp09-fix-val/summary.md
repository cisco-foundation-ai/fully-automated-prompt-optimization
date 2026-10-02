# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.56
- recall: 63.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.008 |
| summarize_hop1 | 5.070 | 4.061 | 10.014 |
| query_hop2 | 0.933 | 0.573 | 2.066 |
| retrieve_hop2 | 0.093 | 0.002 | 1.255 |
| summarize_hop2 | 5.005 | 4.081 | 10.109 |
| query_hop3 | 1.064 | 0.617 | 1.702 |
| retrieve_hop3 | 0.454 | 0.002 | 1.544 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.635** | **10.856** | **24.825** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 111 |
