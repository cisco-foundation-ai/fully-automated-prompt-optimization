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
| retrieve_hop1 | 0.023 | 0.010 | 0.153 |
| summarize_hop1 | 3.324 | 2.833 | 6.299 |
| query_hop2 | 0.905 | 0.851 | 1.712 |
| retrieve_hop2 | 1.958 | 1.320 | 10.161 |
| summarize_hop2 | 4.307 | 3.932 | 8.181 |
| query_hop3 | 0.864 | 0.778 | 1.332 |
| retrieve_hop3 | 5.631 | 3.156 | 18.220 |
| retrieve_mining | 0.058 | 0.038 | 0.060 |
| title_oracle_llm | 2.574 | 1.119 | 9.743 |
| retrieve_oracle | 0.854 | 0.000 | 5.913 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **20.497** | **18.200** | **39.416** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
