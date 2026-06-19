# Evaluation Summary

Total cases: 150

## Composite Score
- average: 95.33

## Score Breakdown
- num_found: 2.95
- num_gold: 3.00
- num_missing: 0.05
- partial_recall: 98.44
- recall: 95.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.466 | 5.002 | 9.299 |
| summarize_hop1 | 1.716 | 1.488 | 3.366 |
| retrieve_hop2 | 8.713 | 8.765 | 14.964 |
| summarize_hop2 | 1.563 | 1.419 | 3.174 |
| retrieve_hop3 | 4.887 | 3.405 | 12.295 |
| summarize_hop3 | 1.381 | 1.226 | 2.515 |
| retrieve_hop4 | 2.269 | 1.665 | 5.636 |
| entity_sweep | 87.347 | 87.835 | 102.360 |
| combine_retrievals | 0.348 | 0.356 | 0.423 |
| **Total** | **113.689** | **113.641** | **137.471** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_sweep | 7 |
