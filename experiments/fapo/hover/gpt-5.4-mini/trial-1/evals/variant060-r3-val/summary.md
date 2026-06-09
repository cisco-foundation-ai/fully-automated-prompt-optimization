# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.33

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- partial_recall: 92.11
- recall: 79.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.006 |
| summarize_hop1 | 2.699 | 2.488 | 4.491 |
| query_hop2 | 0.938 | 0.836 | 1.608 |
| retrieve_hop2 | 0.833 | 1.049 | 1.542 |
| summarize_hop2 | 4.628 | 3.599 | 7.475 |
| query_hop3 | 1.017 | 0.869 | 2.025 |
| retrieve_hop3 | 0.347 | 0.002 | 1.475 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.488** | **9.216** | **15.307** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 62 |
