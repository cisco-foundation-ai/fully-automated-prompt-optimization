# Evaluation Summary

Total cases: 75

## Composite Score
- average: 89.33

## Score Breakdown
- num_found: 2.85
- num_gold: 3.00
- partial_recall: 95.11
- recall: 89.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.010 | 0.165 |
| summarize_hop1 | 3.153 | 2.719 | 5.242 |
| query_hop2 | 1.028 | 0.742 | 1.703 |
| retrieve_hop2 | 2.001 | 1.536 | 6.540 |
| summarize_hop2 | 4.544 | 3.631 | 11.960 |
| query_hop3 | 0.846 | 0.790 | 1.241 |
| retrieve_hop3 | 5.553 | 1.670 | 16.546 |
| retrieve_mining | 0.038 | 0.036 | 0.061 |
| title_oracle_llm | 1.893 | 0.967 | 7.710 |
| retrieve_oracle | 0.634 | 0.000 | 5.210 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **19.717** | **17.078** | **39.545** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
