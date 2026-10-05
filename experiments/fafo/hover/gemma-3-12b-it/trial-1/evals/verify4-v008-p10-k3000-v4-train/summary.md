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
| retrieve_hop1 | 5.984 | 5.552 | 10.328 |
| summarize_hop1 | 1.642 | 1.356 | 3.416 |
| retrieve_hop2 | 10.303 | 8.875 | 20.177 |
| summarize_hop2 | 2.505 | 1.255 | 2.458 |
| retrieve_hop3 | 4.393 | 3.291 | 14.671 |
| summarize_hop3 | 1.373 | 1.208 | 2.638 |
| retrieve_hop4 | 2.564 | 1.737 | 6.604 |
| combine_retrievals | 0.064 | 0.048 | 0.155 |
| **Total** | **28.828** | **24.809** | **49.602** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 14 |
