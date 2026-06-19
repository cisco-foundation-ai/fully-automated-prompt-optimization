# Evaluation Summary

Total cases: 75

## Composite Score
- average: 72.00

## Score Breakdown
- num_found: 2.64
- num_gold: 3.00
- partial_recall: 88.00
- recall: 72.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.030 | 0.012 | 0.180 |
| summarize_hop1 | 8.167 | 5.910 | 23.722 |
| query_hop2 | 1.140 | 0.893 | 2.021 |
| retrieve_hop2 | 3.776 | 1.643 | 12.685 |
| summarize_hop2 | 8.424 | 6.007 | 26.490 |
| query_hop3 | 1.832 | 1.064 | 4.436 |
| retrieve_hop3 | 11.191 | 8.884 | 24.859 |
| retrieve_mining | 0.427 | 0.063 | 1.595 |
| title_oracle_llm | 3.118 | 1.112 | 6.284 |
| retrieve_oracle | 0.369 | 0.001 | 2.790 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **38.473** | **33.255** | **81.861** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 21 |
