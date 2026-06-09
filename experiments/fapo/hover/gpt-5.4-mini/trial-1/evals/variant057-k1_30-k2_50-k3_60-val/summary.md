# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.33

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- partial_recall: 91.22
- recall: 77.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.876 | 2.651 | 4.878 |
| query_hop2 | 0.899 | 0.819 | 1.249 |
| retrieve_hop2 | 1.195 | 1.385 | 1.605 |
| summarize_hop2 | 4.582 | 4.058 | 8.354 |
| query_hop3 | 1.096 | 0.899 | 2.287 |
| retrieve_hop3 | 1.405 | 1.466 | 1.588 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.057** | **11.587** | **17.735** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 68 |
