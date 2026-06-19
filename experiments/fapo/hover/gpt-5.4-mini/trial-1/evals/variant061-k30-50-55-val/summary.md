# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.00

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- partial_recall: 92.22
- recall: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.004 |
| summarize_hop1 | 2.915 | 2.529 | 5.134 |
| query_hop2 | 1.072 | 0.817 | 1.741 |
| retrieve_hop2 | 0.790 | 0.699 | 1.559 |
| summarize_hop2 | 4.150 | 3.712 | 7.548 |
| query_hop3 | 1.241 | 0.905 | 3.319 |
| retrieve_hop3 | 1.466 | 1.421 | 1.570 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.638** | **10.612** | **18.638** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 63 |
