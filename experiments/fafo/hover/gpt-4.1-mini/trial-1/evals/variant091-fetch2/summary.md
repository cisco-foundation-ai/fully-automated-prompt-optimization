# Evaluation Summary

Total cases: 75

## Composite Score
- average: 89.33

## Score Breakdown
- num_found: 2.88
- num_gold: 3.00
- partial_recall: 96.00
- recall: 89.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.011 | 0.181 |
| summarize_hop1 | 3.055 | 2.631 | 4.897 |
| query_hop2 | 1.021 | 0.779 | 1.860 |
| retrieve_hop2 | 3.786 | 2.692 | 14.426 |
| summarize_hop2 | 4.118 | 3.478 | 7.735 |
| query_hop3 | 1.063 | 0.862 | 1.583 |
| retrieve_hop3 | 5.799 | 5.272 | 13.759 |
| retrieve_mining | 0.043 | 0.039 | 0.062 |
| title_oracle_llm | 2.320 | 0.937 | 10.024 |
| retrieve_oracle | 1.102 | 0.002 | 8.358 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **22.330** | **20.738** | **43.460** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
