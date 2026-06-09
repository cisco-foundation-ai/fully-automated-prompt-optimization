# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.33

## Score Breakdown
- num_found: 2.59
- num_gold: 3.00
- partial_recall: 86.44
- recall: 62.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.004 | 0.010 |
| summarize_hop1 | 13.314 | 9.071 | 30.067 |
| query_hop2 | 0.889 | 0.681 | 1.765 |
| retrieve_hop2 | 3.073 | 3.160 | 4.851 |
| summarize_hop2 | 22.449 | 8.498 | 62.500 |
| query_hop3 | 0.924 | 0.718 | 1.617 |
| retrieve_hop3 | 2.893 | 3.115 | 4.795 |
| combine_retrievals | 0.001 | 0.001 | 0.002 |
| **Total** | **43.552** | **29.171** | **92.473** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 111 |
| query_hop2 | 2 |
