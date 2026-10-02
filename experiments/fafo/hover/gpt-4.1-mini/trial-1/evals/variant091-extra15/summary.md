# Evaluation Summary

Total cases: 75

## Composite Score
- average: 88.00

## Score Breakdown
- num_found: 2.85
- num_gold: 3.00
- partial_recall: 95.11
- recall: 88.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.123 | 0.014 | 2.620 |
| summarize_hop1 | 3.319 | 2.837 | 8.104 |
| query_hop2 | 1.176 | 0.718 | 2.147 |
| retrieve_hop2 | 2.028 | 1.620 | 6.189 |
| summarize_hop2 | 4.541 | 3.391 | 8.261 |
| query_hop3 | 1.229 | 0.890 | 2.112 |
| retrieve_hop3 | 5.140 | 3.084 | 17.035 |
| retrieve_mining | 0.038 | 0.037 | 0.055 |
| title_oracle_llm | 2.471 | 0.910 | 9.481 |
| retrieve_oracle | 1.260 | 0.002 | 7.988 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **22.326** | **18.946** | **45.363** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 9 |
