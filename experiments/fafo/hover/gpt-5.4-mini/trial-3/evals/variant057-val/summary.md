# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.00

## Score Breakdown
- num_found: 2.49
- num_gold: 3.00
- num_missing: 0.51
- partial_recall: 83.11
- recall: 57.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.009 |
| summarize_hop1 | 2.941 | 2.610 | 5.321 |
| query_hop2 | 0.867 | 0.762 | 1.240 |
| retrieve_hop2 | 1.149 | 1.329 | 1.687 |
| summarize_hop2 | 3.450 | 3.098 | 6.197 |
| query_hop3 | 0.811 | 0.736 | 1.135 |
| retrieve_hop3 | 1.132 | 1.334 | 1.671 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **10.360** | **9.863** | **15.340** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 129 |
