# Evaluation Summary

Total cases: 300

## Composite Score
- average: 81.00

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- partial_recall: 92.33
- recall: 81.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 2.675 | 2.459 | 4.464 |
| query_hop2 | 0.935 | 0.821 | 1.632 |
| retrieve_hop2 | 1.122 | 1.283 | 1.601 |
| summarize_hop2 | 4.083 | 3.622 | 8.021 |
| query_hop3 | 1.188 | 0.926 | 1.901 |
| retrieve_hop3 | 0.759 | 1.215 | 1.575 |
| query_hop4 | 1.271 | 0.986 | 2.318 |
| retrieve_hop4 | 1.190 | 1.469 | 1.594 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.227** | **12.618** | **20.183** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 57 |
