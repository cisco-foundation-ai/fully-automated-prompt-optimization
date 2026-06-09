# Evaluation Summary

Total cases: 150

## Composite Score
- average: 86.67

## Score Breakdown
- num_found: 2.87
- num_gold: 3.00
- num_missing: 0.13
- partial_recall: 95.56
- recall: 86.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.666 | 5.319 | 10.431 |
| summarize_hop1 | 2.547 | 1.998 | 6.127 |
| retrieve_hop2 | 5.425 | 6.161 | 7.986 |
| summarize_hop2 | 2.047 | 1.641 | 4.206 |
| retrieve_hop3 | 4.749 | 4.963 | 8.002 |
| combine_retrievals | 0.019 | 0.018 | 0.038 |
| **Total** | **20.453** | **20.340** | **30.737** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 20 |
