# Evaluation Summary

Total cases: 75

## Composite Score
- average: 90.67

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- partial_recall: 96.44
- recall: 90.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.011 | 0.158 |
| summarize_hop1 | 3.319 | 2.586 | 8.424 |
| query_hop2 | 1.176 | 0.822 | 3.489 |
| retrieve_hop2 | 2.501 | 1.317 | 13.101 |
| summarize_hop2 | 4.367 | 3.315 | 10.444 |
| query_hop3 | 0.976 | 0.907 | 1.761 |
| retrieve_hop3 | 4.771 | 3.323 | 15.188 |
| retrieve_mining | 4.901 | 4.305 | 9.379 |
| title_oracle_llm | 1.684 | 0.972 | 7.974 |
| retrieve_oracle | 0.489 | 0.001 | 3.194 |
| title_oracle_llm_2 | 7.443 | 6.234 | 15.764 |
| retrieve_oracle_2 | 1.296 | 0.000 | 6.961 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **32.944** | **30.677** | **51.395** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle_2 | 6 |
| retrieve_oracle | 3 |
| title_oracle_llm_2 | 2 |
