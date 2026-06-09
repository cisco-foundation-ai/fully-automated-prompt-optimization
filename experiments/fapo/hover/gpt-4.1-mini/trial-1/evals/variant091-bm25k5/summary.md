# Evaluation Summary

Total cases: 75

## Composite Score
- average: 86.67

## Score Breakdown
- num_found: 2.84
- num_gold: 3.00
- partial_recall: 94.67
- recall: 86.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.010 | 0.114 |
| summarize_hop1 | 2.809 | 2.427 | 4.488 |
| query_hop2 | 1.045 | 0.780 | 2.072 |
| retrieve_hop2 | 2.372 | 1.493 | 13.303 |
| summarize_hop2 | 4.282 | 3.322 | 10.077 |
| query_hop3 | 0.923 | 0.813 | 1.802 |
| retrieve_hop3 | 5.305 | 3.243 | 16.099 |
| retrieve_mining | 0.042 | 0.039 | 0.067 |
| title_oracle_llm | 1.913 | 0.952 | 6.595 |
| retrieve_oracle | 1.408 | 0.001 | 8.928 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **20.122** | **18.305** | **37.308** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 10 |
