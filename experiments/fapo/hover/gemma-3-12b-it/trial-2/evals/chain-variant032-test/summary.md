# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.67

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.67
- recall: 75.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.137 | 1.301 | 1.719 |
| summarize_hop1 | 3.468 | 2.698 | 7.287 |
| query_hop2 | 0.413 | 0.316 | 0.856 |
| retrieve_hop2 | 0.541 | 0.006 | 1.592 |
| summarize_hop2 | 7.730 | 6.088 | 10.669 |
| query_hop3 | 0.400 | 0.334 | 0.517 |
| retrieve_hop3 | 1.087 | 1.344 | 1.637 |
| summarize_hop3 | 8.378 | 6.774 | 13.709 |
| query_hop4 | 0.505 | 0.416 | 0.900 |
| retrieve_hop4 | 1.376 | 1.468 | 1.661 |
| query_hop5 | 0.610 | 0.477 | 0.990 |
| retrieve_hop5 | 2.815 | 2.974 | 3.248 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.460** | **25.378** | **36.902** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 73 |
