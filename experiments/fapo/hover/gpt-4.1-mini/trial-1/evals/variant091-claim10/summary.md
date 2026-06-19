# Evaluation Summary

Total cases: 75

## Composite Score
- average: 92.00

## Score Breakdown
- num_found: 2.91
- num_gold: 3.00
- partial_recall: 96.89
- recall: 92.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.961 | 0.018 | 2.759 |
| summarize_hop1 | 3.639 | 2.787 | 8.456 |
| query_hop2 | 0.871 | 0.761 | 1.519 |
| retrieve_hop2 | 1.753 | 1.519 | 4.778 |
| summarize_hop2 | 4.473 | 3.374 | 10.250 |
| query_hop3 | 1.005 | 0.850 | 2.248 |
| retrieve_hop3 | 3.515 | 1.708 | 10.686 |
| retrieve_mining | 0.073 | 0.037 | 0.082 |
| title_oracle_llm | 1.978 | 1.048 | 8.236 |
| retrieve_oracle | 0.584 | 0.002 | 2.986 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **18.853** | **16.592** | **37.783** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_oracle | 6 |
