# Evaluation Summary

Total cases: 75

## Composite Score
- average: 92.00

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- partial_recall: 96.44
- recall: 92.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.049 | 0.012 | 0.268 |
| summarize_hop1 | 2.946 | 2.544 | 4.726 |
| query_hop2 | 1.073 | 0.793 | 2.026 |
| retrieve_hop2 | 2.621 | 1.600 | 13.152 |
| summarize_hop2 | 4.750 | 3.571 | 14.068 |
| query_hop3 | 1.532 | 0.872 | 3.115 |
| retrieve_hop3 | 6.664 | 4.601 | 19.338 |
| retrieve_mining | 0.065 | 0.041 | 0.075 |
| title_oracle_llm | 2.425 | 0.894 | 10.048 |
| retrieve_oracle | 1.867 | 0.002 | 14.022 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **23.993** | **19.578** | **57.571** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 6 |
