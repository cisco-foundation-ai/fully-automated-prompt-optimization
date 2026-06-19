# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- num_found: 2.60
- num_gold: 3.00
- partial_recall: 86.67
- recall: 67.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.061 | 0.010 | 0.028 |
| summarize_hop1 | 5.254 | 4.056 | 12.182 |
| query_hop2 | 0.840 | 0.771 | 1.291 |
| retrieve_hop2 | 1.811 | 1.535 | 4.725 |
| summarize_hop2 | 5.188 | 4.369 | 12.110 |
| query_hop3 | 1.007 | 0.915 | 1.706 |
| retrieve_hop3 | 4.332 | 3.272 | 10.632 |
| retrieve_mining | 0.152 | 0.024 | 1.078 |
| title_oracle_llm | 5.606 | 3.538 | 14.801 |
| retrieve_oracle | 5.485 | 3.178 | 17.430 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **29.736** | **28.556** | **50.432** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 97 |
