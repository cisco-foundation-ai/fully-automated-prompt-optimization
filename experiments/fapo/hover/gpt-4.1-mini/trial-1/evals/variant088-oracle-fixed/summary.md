# Evaluation Summary

Total cases: 75

## Composite Score
- average: 88.00

## Score Breakdown
- num_found: 2.84
- num_gold: 3.00
- partial_recall: 94.67
- recall: 88.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.013 | 0.147 |
| summarize_hop1 | 4.175 | 3.568 | 9.123 |
| query_hop2 | 1.128 | 0.804 | 1.631 |
| retrieve_hop2 | 6.280 | 4.572 | 15.949 |
| summarize_hop2 | 4.946 | 4.143 | 10.688 |
| query_hop3 | 1.310 | 0.928 | 2.528 |
| retrieve_hop3 | 12.521 | 10.580 | 32.577 |
| retrieve_mining | 0.367 | 0.043 | 2.141 |
| title_oracle_llm | 1.831 | 1.192 | 5.749 |
| retrieve_oracle | 0.859 | 0.002 | 3.928 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **33.442** | **30.663** | **58.848** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 9 |
