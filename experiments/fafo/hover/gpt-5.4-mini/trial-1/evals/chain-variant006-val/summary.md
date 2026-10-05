# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- partial_recall: 88.33
- recall: 70.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.404 | 2.162 | 3.837 |
| query_hop2 | 0.907 | 0.759 | 1.077 |
| retrieve_hop2 | 1.404 | 1.397 | 1.687 |
| summarize_hop2 | 1.977 | 1.738 | 3.026 |
| query_hop3 | 0.664 | 0.609 | 0.940 |
| retrieve_hop3 | 0.289 | 0.002 | 1.565 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.648** | **7.025** | **10.892** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 88 |
