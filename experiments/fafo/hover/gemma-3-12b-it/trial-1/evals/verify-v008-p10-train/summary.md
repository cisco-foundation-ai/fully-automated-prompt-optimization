# Evaluation Summary

Total cases: 150

## Composite Score
- average: 88.00

## Score Breakdown
- num_found: 2.88
- num_gold: 3.00
- num_missing: 0.12
- partial_recall: 96.00
- recall: 88.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.695 | 4.530 | 9.505 |
| summarize_hop1 | 1.488 | 1.288 | 3.012 |
| retrieve_hop2 | 4.430 | 4.542 | 8.002 |
| summarize_hop2 | 1.430 | 1.289 | 2.599 |
| retrieve_hop3 | 3.164 | 2.710 | 7.554 |
| combine_retrievals | 0.017 | 0.015 | 0.038 |
| **Total** | **15.226** | **15.431** | **25.537** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 18 |
