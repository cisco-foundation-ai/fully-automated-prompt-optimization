# Evaluation Summary

Total cases: 300

## Composite Score
- average: 25.33

## Score Breakdown
- num_found: 1.90
- num_gold: 3.00
- partial_recall: 63.33
- recall: 25.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.004 |
| summarize_hop1 | 4.929 | 3.536 | 11.311 |
| query_hop2 | 1.726 | 1.078 | 3.964 |
| retrieve_hop2 | 1.398 | 1.339 | 1.696 |
| summarize_hop2 | 5.590 | 4.491 | 13.194 |
| query_hop3 | 1.711 | 1.156 | 5.282 |
| retrieve_hop3 | 1.196 | 1.340 | 1.683 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **16.554** | **14.220** | **33.241** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 224 |
