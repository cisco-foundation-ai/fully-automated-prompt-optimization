# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.33
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.009 |
| summarize_hop1 | 2.403 | 2.134 | 3.714 |
| query_hop2 | 0.910 | 0.714 | 1.250 |
| retrieve_hop2 | 0.918 | 1.094 | 1.641 |
| summarize_hop2 | 2.066 | 1.845 | 3.081 |
| query_hop3 | 0.684 | 0.591 | 0.889 |
| retrieve_hop3 | 0.204 | 0.002 | 1.569 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.200** | **6.545** | **11.349** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 83 |
