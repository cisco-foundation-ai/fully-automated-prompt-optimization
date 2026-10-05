# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- partial_recall: 89.78
- recall: 72.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.009 |
| summarize_hop1 | 2.423 | 2.251 | 3.543 |
| query_hop2 | 0.782 | 0.692 | 1.051 |
| retrieve_hop2 | 1.103 | 1.510 | 1.676 |
| summarize_hop2 | 2.015 | 1.757 | 3.047 |
| query_hop3 | 0.625 | 0.581 | 0.974 |
| retrieve_hop3 | 0.108 | 0.002 | 1.515 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.075** | **6.565** | **11.142** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 82 |
