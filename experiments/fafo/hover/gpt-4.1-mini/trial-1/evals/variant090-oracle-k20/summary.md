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
| retrieve_hop1 | 0.025 | 0.013 | 0.136 |
| summarize_hop1 | 2.881 | 2.577 | 5.313 |
| query_hop2 | 1.191 | 0.804 | 1.860 |
| retrieve_hop2 | 2.154 | 1.366 | 12.821 |
| summarize_hop2 | 4.428 | 4.074 | 8.437 |
| query_hop3 | 1.200 | 0.858 | 2.639 |
| retrieve_hop3 | 6.571 | 5.166 | 21.923 |
| retrieve_mining | 0.081 | 0.044 | 0.106 |
| title_oracle_llm | 1.788 | 0.946 | 7.688 |
| retrieve_oracle | 1.099 | 0.001 | 5.169 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **21.418** | **20.303** | **38.290** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 6 |
