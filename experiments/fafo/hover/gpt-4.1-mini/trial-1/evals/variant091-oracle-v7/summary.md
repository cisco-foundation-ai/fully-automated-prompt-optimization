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
| retrieve_hop1 | 1.880 | 1.317 | 15.126 |
| summarize_hop1 | 3.147 | 2.815 | 6.402 |
| query_hop2 | 0.843 | 0.798 | 1.337 |
| retrieve_hop2 | 1.774 | 1.548 | 4.612 |
| summarize_hop2 | 5.438 | 3.792 | 9.566 |
| query_hop3 | 0.909 | 0.798 | 1.587 |
| retrieve_hop3 | 4.458 | 3.119 | 13.533 |
| retrieve_mining | 0.574 | 0.041 | 3.053 |
| title_oracle_llm | 3.180 | 1.435 | 11.995 |
| retrieve_oracle | 4.455 | 2.643 | 13.998 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **26.657** | **23.683** | **50.471** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 8 |
