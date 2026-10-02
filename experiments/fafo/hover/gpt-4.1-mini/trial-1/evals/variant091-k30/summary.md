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
| retrieve_hop1 | 1.740 | 1.119 | 14.012 |
| summarize_hop1 | 3.645 | 3.075 | 9.538 |
| query_hop2 | 1.160 | 0.775 | 2.563 |
| retrieve_hop2 | 1.983 | 1.602 | 4.632 |
| summarize_hop2 | 6.127 | 4.260 | 12.711 |
| query_hop3 | 0.975 | 0.887 | 1.616 |
| retrieve_hop3 | 5.820 | 3.455 | 17.484 |
| retrieve_mining | 0.061 | 0.037 | 0.066 |
| title_oracle_llm | 2.667 | 1.044 | 13.218 |
| retrieve_oracle | 0.753 | 0.001 | 6.119 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **24.931** | **23.273** | **56.432** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 10 |
