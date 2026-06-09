# Evaluation Summary

Total cases: 300

## Composite Score
- average: 91.33

## Score Breakdown
- num_found: 2.90
- num_gold: 3.00
- partial_recall: 96.78
- recall: 91.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.511 | 0.022 | 5.045 |
| summarize_hop1 | 3.206 | 2.600 | 5.745 |
| query_hop2 | 1.002 | 0.774 | 1.483 |
| retrieve_hop2 | 2.658 | 1.609 | 8.830 |
| summarize_hop2 | 4.053 | 3.390 | 8.985 |
| query_hop3 | 1.225 | 0.895 | 1.850 |
| retrieve_hop3 | 8.377 | 5.917 | 25.735 |
| retrieve_mining | 0.108 | 0.042 | 0.089 |
| title_oracle_llm | 2.381 | 1.057 | 8.812 |
| retrieve_oracle | 1.546 | 0.001 | 7.738 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **26.066** | **22.976** | **53.081** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 26 |
