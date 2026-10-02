# Evaluation Summary

Total cases: 150

## Composite Score
- average: 96.00

## Score Breakdown
- num_found: 2.96
- num_gold: 3.00
- num_missing: 0.04
- partial_recall: 98.67
- recall: 96.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.141 | 4.214 | 6.559 |
| summarize_hop1 | 1.734 | 1.458 | 3.328 |
| retrieve_hop2 | 6.478 | 6.361 | 11.551 |
| summarize_hop2 | 1.537 | 1.321 | 3.524 |
| retrieve_hop3 | 3.589 | 3.143 | 8.470 |
| summarize_hop3 | 1.370 | 1.091 | 3.009 |
| retrieve_hop4 | 1.742 | 1.194 | 4.316 |
| entity_sweep | 58.357 | 56.877 | 72.003 |
| combine_retrievals | 0.130 | 0.130 | 0.190 |
| **Total** | **79.079** | **76.596** | **102.120** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_sweep | 6 |
