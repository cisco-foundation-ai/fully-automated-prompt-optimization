# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- partial_recall: 90.67
- recall: 76.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.002 | 0.008 |
| summarize_hop1 | 2.422 | 2.272 | 3.802 |
| query_hop2 | 0.805 | 0.676 | 1.175 |
| retrieve_hop2 | 0.761 | 0.003 | 1.662 |
| summarize_hop2 | 3.504 | 3.124 | 5.752 |
| query_hop3 | 0.851 | 0.719 | 1.414 |
| retrieve_hop3 | 0.708 | 0.529 | 1.654 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.075** | **8.915** | **13.081** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 71 |
