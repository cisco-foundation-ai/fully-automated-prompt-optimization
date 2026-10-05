# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.33

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 91.00
- recall: 76.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 5.676 | 5.537 | 8.685 |
| query_hop2 | 0.373 | 0.314 | 0.682 |
| retrieve_hop2 | 0.926 | 0.250 | 1.667 |
| summarize_hop2 | 7.338 | 6.304 | 11.020 |
| query_hop3 | 0.385 | 0.350 | 0.632 |
| retrieve_hop3 | 1.297 | 1.559 | 1.687 |
| summarize_hop3 | 9.923 | 7.973 | 14.876 |
| query_hop4 | 0.505 | 0.447 | 0.774 |
| retrieve_hop4 | 1.513 | 1.607 | 1.708 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **27.939** | **25.201** | **37.344** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 71 |
