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
| retrieve_hop1 | 0.027 | 0.012 | 0.168 |
| summarize_hop1 | 3.284 | 2.727 | 7.863 |
| query_hop2 | 0.869 | 0.748 | 1.485 |
| retrieve_hop2 | 2.403 | 1.518 | 13.768 |
| summarize_hop2 | 3.989 | 3.629 | 7.438 |
| query_hop3 | 1.013 | 0.860 | 2.266 |
| retrieve_hop3 | 5.815 | 3.961 | 19.067 |
| retrieve_mining | 0.046 | 0.043 | 0.065 |
| title_oracle_llm | 1.992 | 0.965 | 3.748 |
| retrieve_oracle | 0.433 | 0.002 | 2.859 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **19.869** | **17.551** | **42.986** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
