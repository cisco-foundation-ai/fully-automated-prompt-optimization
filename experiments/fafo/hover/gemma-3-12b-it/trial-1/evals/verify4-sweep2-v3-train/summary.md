# Evaluation Summary

Total cases: 150

## Composite Score
- average: 98.00

## Score Breakdown
- num_found: 2.98
- num_gold: 3.00
- num_missing: 0.02
- partial_recall: 99.33
- recall: 98.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.285 | 5.287 | 7.882 |
| summarize_hop1 | 1.964 | 1.421 | 5.092 |
| retrieve_hop2 | 8.402 | 8.491 | 13.491 |
| summarize_hop2 | 1.823 | 1.466 | 3.997 |
| retrieve_hop3 | 4.622 | 3.172 | 11.630 |
| summarize_hop3 | 1.460 | 1.202 | 3.722 |
| retrieve_hop4 | 2.169 | 1.576 | 5.812 |
| entity_sweep | 74.293 | 75.962 | 84.586 |
| combine_retrievals | 0.130 | 0.132 | 0.188 |
| **Total** | **100.147** | **100.894** | **122.380** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_sweep | 3 |
