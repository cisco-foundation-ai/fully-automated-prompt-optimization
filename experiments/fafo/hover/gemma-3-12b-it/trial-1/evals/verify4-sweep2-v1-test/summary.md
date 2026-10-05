# Evaluation Summary

Total cases: 300

## Composite Score
- average: 93.00

## Score Breakdown
- num_found: 2.92
- num_gold: 3.00
- num_missing: 0.08
- partial_recall: 97.44
- recall: 93.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.950 | 4.785 | 8.080 |
| summarize_hop1 | 1.912 | 1.423 | 3.882 |
| retrieve_hop2 | 8.511 | 8.745 | 14.206 |
| summarize_hop2 | 1.649 | 1.335 | 3.772 |
| retrieve_hop3 | 4.093 | 3.179 | 10.851 |
| summarize_hop3 | 1.412 | 1.234 | 2.975 |
| retrieve_hop4 | 2.125 | 1.607 | 6.237 |
| entity_sweep | 74.561 | 77.897 | 89.465 |
| combine_retrievals | 0.127 | 0.127 | 0.195 |
| **Total** | **99.340** | **100.712** | **124.926** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_sweep | 21 |
