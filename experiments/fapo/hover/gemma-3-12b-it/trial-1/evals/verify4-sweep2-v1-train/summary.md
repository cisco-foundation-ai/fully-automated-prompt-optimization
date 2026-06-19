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
| retrieve_hop1 | 3.660 | 4.053 | 8.043 |
| summarize_hop1 | 1.709 | 1.430 | 3.478 |
| retrieve_hop2 | 6.613 | 6.336 | 13.698 |
| summarize_hop2 | 1.490 | 1.266 | 2.924 |
| retrieve_hop3 | 3.751 | 2.584 | 10.705 |
| summarize_hop3 | 1.447 | 1.171 | 3.295 |
| retrieve_hop4 | 1.741 | 1.401 | 4.963 |
| entity_sweep | 70.542 | 71.374 | 87.437 |
| combine_retrievals | 0.130 | 0.128 | 0.190 |
| **Total** | **91.082** | **90.957** | **117.920** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_sweep | 7 |
