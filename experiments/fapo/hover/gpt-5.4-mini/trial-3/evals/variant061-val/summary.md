# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- num_found: 2.66
- num_gold: 3.00
- num_missing: 0.34
- partial_recall: 88.56
- recall: 68.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.976 | 0.546 | 1.681 |
| summarize_hop1 | 8.529 | 8.041 | 13.905 |
| query_hop2 | 1.053 | 0.776 | 1.547 |
| retrieve_hop2 | 1.148 | 1.273 | 1.624 |
| summarize_hop2 | 3.016 | 2.569 | 5.195 |
| query_hop3 | 0.978 | 0.772 | 1.891 |
| retrieve_hop3 | 1.226 | 1.293 | 1.621 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **16.927** | **16.099** | **26.727** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 94 |
