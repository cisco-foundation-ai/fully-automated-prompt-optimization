# Evaluation Summary

Total cases: 300

## Composite Score
- average: 81.00

## Score Breakdown
- num_found: 2.78
- num_gold: 3.00
- num_missing: 0.22
- partial_recall: 92.78
- recall: 81.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.637 | 2.984 | 7.515 |
| query_hop2 | 0.441 | 0.331 | 1.148 |
| retrieve_hop2 | 0.834 | 1.050 | 1.609 |
| summarize_hop2 | 8.085 | 6.216 | 11.862 |
| query_hop3 | 0.527 | 0.382 | 1.617 |
| retrieve_hop3 | 1.873 | 1.856 | 3.172 |
| summarize_hop3 | 7.438 | 7.240 | 13.762 |
| query_hop4 | 0.600 | 0.425 | 1.577 |
| retrieve_hop4 | 1.280 | 1.329 | 1.652 |
| query_hop5 | 0.773 | 0.549 | 2.213 |
| retrieve_hop5 | 3.961 | 3.917 | 4.854 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **29.452** | **27.389** | **39.717** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 57 |
