# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.33

## Score Breakdown
- num_found: 1.84
- num_gold: 3.00
- num_missing: 1.16
- partial_recall: 61.22
- recall: 23.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 1.718 | 1.465 | 2.251 |
| query_hop2 | 0.945 | 0.776 | 1.469 |
| retrieve_hop2 | 1.362 | 1.515 | 1.646 |
| summarize_hop2 | 2.085 | 1.823 | 2.683 |
| query_hop3 | 0.845 | 0.739 | 1.137 |
| retrieve_hop3 | 1.157 | 1.339 | 1.651 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.115** | **7.620** | **12.152** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 230 |
