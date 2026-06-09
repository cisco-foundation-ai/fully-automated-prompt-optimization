# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- partial_recall: 87.78
- recall: 70.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.404 | 0.019 | 2.150 |
| summarize_hop1 | 7.512 | 5.024 | 21.988 |
| query_hop2 | 1.156 | 0.891 | 2.249 |
| retrieve_hop2 | 4.202 | 2.600 | 12.804 |
| summarize_hop2 | 6.675 | 4.915 | 15.443 |
| query_hop3 | 1.345 | 1.026 | 3.009 |
| retrieve_hop3 | 8.908 | 7.343 | 21.472 |
| retrieve_mining | 0.239 | 0.051 | 1.539 |
| title_oracle_llm | 1.537 | 1.194 | 3.093 |
| retrieve_oracle | 0.466 | 0.000 | 2.616 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **32.445** | **29.136** | **60.542** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 88 |
