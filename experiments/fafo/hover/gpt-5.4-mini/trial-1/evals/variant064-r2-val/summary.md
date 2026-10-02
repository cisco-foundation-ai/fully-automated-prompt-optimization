# Evaluation Summary

Total cases: 300

## Composite Score
- average: 83.33

## Score Breakdown
- num_found: 2.81
- num_gold: 3.00
- partial_recall: 93.78
- recall: 83.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.005 |
| summarize_hop1 | 3.071 | 2.556 | 4.899 |
| query_hop2 | 1.098 | 0.865 | 2.511 |
| retrieve_hop2 | 0.688 | 0.003 | 1.556 |
| summarize_hop2 | 4.353 | 3.707 | 7.997 |
| query_hop3 | 1.327 | 0.954 | 2.906 |
| retrieve_hop3 | 0.322 | 0.002 | 1.513 |
| query_hop4 | 1.509 | 1.039 | 3.719 |
| retrieve_hop4 | 1.006 | 1.256 | 1.572 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.386** | **12.014** | **21.033** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 50 |
