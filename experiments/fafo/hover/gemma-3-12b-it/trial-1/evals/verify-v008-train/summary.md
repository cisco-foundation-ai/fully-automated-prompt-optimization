# Evaluation Summary

Total cases: 150

## Composite Score
- average: 84.67

## Score Breakdown
- num_found: 2.84
- num_gold: 3.00
- num_missing: 0.16
- partial_recall: 94.67
- recall: 84.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.780 | 5.282 | 9.785 |
| summarize_hop1 | 3.976 | 3.206 | 9.011 |
| retrieve_hop2 | 6.132 | 6.619 | 8.221 |
| summarize_hop2 | 3.080 | 2.542 | 6.934 |
| retrieve_hop3 | 5.317 | 5.787 | 8.239 |
| combine_retrievals | 0.021 | 0.019 | 0.038 |
| **Total** | **24.306** | **24.456** | **35.051** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 23 |
