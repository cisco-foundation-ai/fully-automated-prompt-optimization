# Evaluation Summary

Total cases: 300

## Composite Score
- average: 94.00

## Score Breakdown
- num_found: 2.93
- num_gold: 3.00
- partial_recall: 97.78
- recall: 94.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| query_hop1 | 0.903 | 0.687 | 1.280 |
| retrieve_hop1 | 8.142 | 8.079 | 9.741 |
| summarize_hop1 | 115.132 | 109.494 | 189.051 |
| query_hop2 | 1.261 | 0.757 | 1.197 |
| retrieve_hop2 | 6.957 | 7.571 | 8.137 |
| summarize_hop2 | 23.496 | 18.081 | 43.225 |
| query_hop3 | 0.951 | 0.702 | 1.138 |
| retrieve_hop3 | 5.201 | 5.467 | 7.946 |
| combine_retrievals | 0.003 | 0.002 | 0.012 |
| **Total** | **162.046** | **154.803** | **242.675** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 18 |
