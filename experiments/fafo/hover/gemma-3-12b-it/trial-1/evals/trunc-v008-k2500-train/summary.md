# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- num_missing: 0.31
- partial_recall: 89.78
- recall: 70.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.343 | 1.158 | 1.772 |
| summarize_hop1 | 4.038 | 3.491 | 8.920 |
| query_hop2 | 0.370 | 0.290 | 0.791 |
| retrieve_hop2 | 1.383 | 1.493 | 1.653 |
| summarize_hop2 | 2.805 | 2.155 | 6.262 |
| query_hop3 | 0.318 | 0.280 | 0.599 |
| retrieve_hop3 | 1.394 | 1.490 | 1.655 |
| combine_retrievals | 0.006 | 0.006 | 0.009 |
| **Total** | **11.655** | **10.739** | **20.796** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 45 |
