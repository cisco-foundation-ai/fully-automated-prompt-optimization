# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- partial_recall: 88.22
- recall: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.010 | 0.569 | 1.711 |
| summarize_hop1 | 18.617 | 14.430 | 43.286 |
| query_hop2 | 0.779 | 0.690 | 1.150 |
| retrieve_hop2 | 5.389 | 6.396 | 8.135 |
| summarize_hop2 | 37.585 | 23.127 | 138.351 |
| query_hop3 | 0.943 | 0.694 | 1.218 |
| retrieve_hop3 | 5.279 | 5.360 | 7.961 |
| combine_retrievals | 0.002 | 0.002 | 0.005 |
| **Total** | **69.605** | **54.848** | **180.263** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 99 |
| query_hop2 | 1 |
