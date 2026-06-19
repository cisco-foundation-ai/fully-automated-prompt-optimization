# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.00

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- partial_recall: 90.89
- recall: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.009 |
| summarize_hop1 | 2.639 | 2.450 | 4.327 |
| query_hop2 | 0.936 | 0.757 | 1.370 |
| retrieve_hop2 | 0.589 | 0.002 | 1.646 |
| summarize_hop2 | 3.949 | 3.534 | 7.092 |
| query_hop3 | 1.082 | 0.788 | 2.208 |
| retrieve_hop3 | 1.060 | 1.331 | 1.633 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.270** | **9.659** | **16.445** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 72 |
