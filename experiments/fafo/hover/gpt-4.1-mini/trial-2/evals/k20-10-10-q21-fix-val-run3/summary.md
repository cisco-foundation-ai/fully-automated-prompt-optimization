# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- num_found: 2.61
- num_gold: 3.00
- partial_recall: 87.00
- recall: 67.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.012 | 0.002 | 0.008 |
| summarize_hop1 | 4.293 | 3.516 | 6.372 |
| query_hop2 | 0.765 | 0.568 | 1.264 |
| retrieve_hop2 | 0.362 | 0.003 | 1.512 |
| summarize_hop2 | 3.901 | 3.538 | 5.989 |
| query_hop3 | 0.815 | 0.583 | 1.599 |
| retrieve_hop3 | 0.513 | 0.003 | 1.545 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.661** | **9.582** | **15.946** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 98 |
