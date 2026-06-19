# Evaluation Summary

Total cases: 300

## Composite Score
- average: 51.67

## Score Breakdown
- num_found: 2.32
- num_gold: 3.00
- partial_recall: 77.22
- recall: 51.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.064 | 1.109 | 1.672 |
| summarize_hop1 | 4.399 | 3.668 | 8.353 |
| query_hop2 | 1.354 | 1.041 | 2.719 |
| retrieve_hop2 | 1.241 | 1.317 | 1.646 |
| summarize_hop2 | 5.069 | 3.917 | 10.127 |
| query_hop3 | 1.498 | 1.096 | 3.169 |
| retrieve_hop3 | 1.221 | 1.325 | 1.630 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **15.846** | **14.223** | **26.008** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 145 |
