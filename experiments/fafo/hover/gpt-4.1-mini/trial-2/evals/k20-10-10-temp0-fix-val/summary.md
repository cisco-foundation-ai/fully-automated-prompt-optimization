# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- num_found: 2.55
- num_gold: 3.00
- partial_recall: 85.00
- recall: 62.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.004 |
| summarize_hop1 | 3.191 | 2.771 | 4.739 |
| query_hop2 | 0.880 | 0.566 | 1.364 |
| retrieve_hop2 | 0.072 | 0.002 | 0.015 |
| summarize_hop2 | 3.402 | 2.944 | 6.286 |
| query_hop3 | 0.790 | 0.589 | 1.317 |
| retrieve_hop3 | 0.399 | 0.002 | 1.431 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.768** | **7.831** | **14.186** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 112 |
