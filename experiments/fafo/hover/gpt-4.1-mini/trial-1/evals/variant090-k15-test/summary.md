# Evaluation Summary

Total cases: 300

## Composite Score
- average: 90.33

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- partial_recall: 96.33
- recall: 90.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.010 | 0.028 |
| summarize_hop1 | 3.221 | 2.692 | 5.648 |
| query_hop2 | 0.860 | 0.772 | 1.337 |
| retrieve_hop2 | 3.110 | 1.632 | 10.295 |
| summarize_hop2 | 4.446 | 3.601 | 9.625 |
| query_hop3 | 1.152 | 0.837 | 1.508 |
| retrieve_hop3 | 9.732 | 7.393 | 27.571 |
| retrieve_mining | 0.656 | 0.042 | 3.884 |
| title_oracle_llm | 2.825 | 1.096 | 10.809 |
| retrieve_oracle | 1.516 | 0.002 | 6.329 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **27.536** | **24.208** | **53.254** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 29 |
