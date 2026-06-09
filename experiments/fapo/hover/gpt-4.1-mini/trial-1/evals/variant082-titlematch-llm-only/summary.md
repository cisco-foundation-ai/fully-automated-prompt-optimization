# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- partial_recall: 87.22
- recall: 69.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.010 | 0.024 |
| summarize_hop1 | 7.146 | 4.586 | 18.821 |
| query_hop2 | 1.076 | 0.871 | 1.743 |
| retrieve_hop2 | 8.579 | 5.996 | 24.754 |
| summarize_hop2 | 5.930 | 4.828 | 13.142 |
| query_hop3 | 1.241 | 0.995 | 2.270 |
| retrieve_hop3 | 18.324 | 18.384 | 37.727 |
| retrieve_mining | 0.188 | 0.022 | 1.542 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **42.499** | **39.888** | **72.294** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 92 |
