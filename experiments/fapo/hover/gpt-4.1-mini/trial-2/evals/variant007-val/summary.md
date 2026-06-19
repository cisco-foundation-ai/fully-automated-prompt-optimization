# Evaluation Summary

Total cases: 300

## Composite Score
- average: 21.67

## Score Breakdown
- num_found: 1.83
- num_gold: 3.00
- partial_recall: 60.89
- recall: 21.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.004 |
| summarize_hop1 | 2.646 | 2.120 | 4.731 |
| query_hop2 | 0.713 | 0.532 | 0.961 |
| retrieve_hop2 | 0.419 | 0.002 | 1.575 |
| summarize_hop2 | 3.333 | 2.534 | 6.776 |
| query_hop3 | 0.954 | 0.518 | 1.442 |
| retrieve_hop3 | 0.349 | 0.002 | 1.585 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.424** | **6.977** | **20.599** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 233 |
| query_hop3 | 2 |
