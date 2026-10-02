# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- partial_recall: 90.44
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.011 |
| summarize_hop1 | 2.563 | 2.354 | 4.050 |
| query_hop2 | 0.864 | 0.709 | 1.312 |
| retrieve_hop2 | 0.381 | 0.002 | 1.472 |
| summarize_hop2 | 3.713 | 3.388 | 6.221 |
| query_hop3 | 0.986 | 0.790 | 1.898 |
| retrieve_hop3 | 0.300 | 0.002 | 1.510 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.849** | **8.311** | **12.948** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 76 |
