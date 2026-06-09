# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.22
- recall: 73.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 2.355 | 2.131 | 3.737 |
| query_hop2 | 0.783 | 0.728 | 1.048 |
| retrieve_hop2 | 1.593 | 1.531 | 1.644 |
| summarize_hop2 | 1.913 | 1.790 | 2.743 |
| query_hop3 | 0.712 | 0.596 | 0.935 |
| retrieve_hop3 | 0.146 | 0.002 | 1.501 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.506** | **6.986** | **10.504** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 80 |
