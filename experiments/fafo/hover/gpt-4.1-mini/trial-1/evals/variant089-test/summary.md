# Evaluation Summary

Total cases: 300

## Composite Score
- average: 90.00

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- partial_recall: 96.33
- recall: 90.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 3.187 | 2.550 | 9.169 |
| summarize_hop1 | 3.493 | 2.781 | 6.676 |
| query_hop2 | 0.979 | 0.786 | 1.582 |
| retrieve_hop2 | 8.757 | 6.769 | 22.626 |
| summarize_hop2 | 4.514 | 3.569 | 9.500 |
| query_hop3 | 1.279 | 0.895 | 2.183 |
| retrieve_hop3 | 14.395 | 13.768 | 31.068 |
| retrieve_mining | 5.325 | 1.536 | 25.664 |
| title_oracle_llm | 2.714 | 1.135 | 10.440 |
| retrieve_oracle | 1.478 | 0.002 | 5.918 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **46.121** | **42.885** | **88.390** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 30 |
