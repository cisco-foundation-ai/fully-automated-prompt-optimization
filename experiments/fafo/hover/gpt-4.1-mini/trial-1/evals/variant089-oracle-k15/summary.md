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
| retrieve_hop1 | 1.761 | 1.087 | 14.042 |
| summarize_hop1 | 4.001 | 3.385 | 7.865 |
| query_hop2 | 0.987 | 0.855 | 1.544 |
| retrieve_hop2 | 2.795 | 1.694 | 7.880 |
| summarize_hop2 | 5.293 | 4.475 | 13.449 |
| query_hop3 | 1.143 | 0.890 | 2.925 |
| retrieve_hop3 | 10.220 | 8.082 | 26.900 |
| retrieve_mining | 0.287 | 0.045 | 1.638 |
| title_oracle_llm | 3.591 | 1.382 | 11.891 |
| retrieve_oracle | 1.976 | 0.002 | 10.442 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **32.053** | **30.925** | **52.955** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
