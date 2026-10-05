# Evaluation Summary

Total cases: 75

## Composite Score
- average: 89.33

## Score Breakdown
- num_found: 2.87
- num_gold: 3.00
- partial_recall: 95.56
- recall: 89.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.044 | 0.012 | 0.172 |
| summarize_hop1 | 2.975 | 2.675 | 4.729 |
| query_hop2 | 0.961 | 0.828 | 2.035 |
| retrieve_hop2 | 3.058 | 1.647 | 13.266 |
| summarize_hop2 | 4.383 | 3.523 | 9.565 |
| query_hop3 | 1.190 | 0.842 | 1.881 |
| retrieve_hop3 | 6.407 | 4.791 | 20.292 |
| retrieve_mining | 0.046 | 0.043 | 0.068 |
| title_oracle_llm | 1.613 | 0.929 | 5.785 |
| retrieve_oracle | 0.526 | 0.000 | 2.665 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **21.203** | **18.684** | **45.222** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
