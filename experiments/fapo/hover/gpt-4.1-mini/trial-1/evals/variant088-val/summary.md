# Evaluation Summary

Total cases: 300

## Composite Score
- average: 92.00

## Score Breakdown
- num_found: 2.91
- num_gold: 3.00
- partial_recall: 97.11
- recall: 92.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.067 | 0.012 | 0.042 |
| summarize_hop1 | 3.577 | 2.868 | 7.507 |
| query_hop2 | 1.214 | 0.825 | 2.672 |
| retrieve_hop2 | 4.836 | 3.250 | 13.136 |
| summarize_hop2 | 5.030 | 3.938 | 11.134 |
| query_hop3 | 1.317 | 0.891 | 2.546 |
| retrieve_hop3 | 13.925 | 13.245 | 32.395 |
| retrieve_mining | 0.333 | 0.045 | 1.592 |
| title_oracle_llm | 2.533 | 1.159 | 8.837 |
| retrieve_oracle | 1.025 | 0.002 | 4.496 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **33.858** | **32.052** | **61.994** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 24 |
