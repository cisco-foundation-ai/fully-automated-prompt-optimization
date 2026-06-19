# Evaluation Summary

Total cases: 75

## Composite Score
- average: 88.00

## Score Breakdown
- num_found: 2.87
- num_gold: 3.00
- partial_recall: 95.56
- recall: 88.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.010 | 0.168 |
| summarize_hop1 | 3.180 | 2.808 | 6.368 |
| query_hop2 | 0.882 | 0.776 | 1.822 |
| retrieve_hop2 | 2.011 | 1.399 | 5.438 |
| summarize_hop2 | 4.232 | 3.377 | 9.556 |
| query_hop3 | 0.933 | 0.784 | 1.477 |
| retrieve_hop3 | 5.073 | 3.203 | 15.296 |
| retrieve_mining | 0.039 | 0.040 | 0.058 |
| title_oracle_llm | 2.275 | 1.003 | 10.388 |
| retrieve_oracle | 0.488 | 0.001 | 3.152 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **19.137** | **17.064** | **44.927** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 9 |
