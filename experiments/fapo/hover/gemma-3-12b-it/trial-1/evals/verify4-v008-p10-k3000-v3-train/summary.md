# Evaluation Summary

Total cases: 150

## Composite Score
- average: 90.67

## Score Breakdown
- num_found: 2.91
- num_gold: 3.00
- num_missing: 0.09
- partial_recall: 96.89
- recall: 90.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.558 | 5.296 | 8.389 |
| summarize_hop1 | 1.518 | 1.256 | 3.366 |
| retrieve_hop2 | 8.033 | 8.352 | 14.119 |
| summarize_hop2 | 1.444 | 1.274 | 2.655 |
| retrieve_hop3 | 4.527 | 3.367 | 11.499 |
| summarize_hop3 | 1.316 | 1.162 | 2.384 |
| retrieve_hop4 | 2.290 | 1.615 | 6.099 |
| combine_retrievals | 0.052 | 0.043 | 0.109 |
| **Total** | **24.739** | **23.743** | **40.009** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 14 |
