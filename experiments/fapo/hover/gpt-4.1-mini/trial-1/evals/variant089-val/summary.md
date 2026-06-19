# Evaluation Summary

Total cases: 300

## Composite Score
- average: 91.00

## Score Breakdown
- num_found: 2.90
- num_gold: 3.00
- partial_recall: 96.67
- recall: 91.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.449 | 0.098 | 1.635 |
| summarize_hop1 | 4.016 | 3.050 | 8.660 |
| query_hop2 | 1.071 | 0.821 | 1.838 |
| retrieve_hop2 | 2.478 | 1.625 | 7.510 |
| summarize_hop2 | 4.861 | 3.909 | 11.152 |
| query_hop3 | 1.218 | 0.966 | 2.155 |
| retrieve_hop3 | 8.875 | 6.665 | 24.373 |
| retrieve_mining | 0.163 | 0.044 | 1.094 |
| title_oracle_llm | 3.530 | 1.245 | 11.706 |
| retrieve_oracle | 1.302 | 0.001 | 6.301 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **27.963** | **24.953** | **60.108** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 27 |
