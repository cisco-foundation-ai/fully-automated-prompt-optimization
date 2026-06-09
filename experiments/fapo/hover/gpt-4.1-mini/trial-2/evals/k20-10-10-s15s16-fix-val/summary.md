# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- num_found: 2.53
- num_gold: 3.00
- partial_recall: 84.44
- recall: 60.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.004 |
| summarize_hop1 | 3.705 | 3.120 | 5.621 |
| query_hop2 | 0.982 | 0.573 | 1.493 |
| retrieve_hop2 | 0.144 | 0.002 | 1.441 |
| summarize_hop2 | 3.906 | 3.531 | 5.999 |
| query_hop3 | 0.819 | 0.592 | 1.515 |
| retrieve_hop3 | 0.780 | 0.002 | 1.545 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.344** | **9.093** | **18.668** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 118 |
