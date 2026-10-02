# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.67

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 90.89
- recall: 75.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.010 |
| summarize_hop1 | 3.304 | 2.656 | 7.316 |
| query_hop2 | 0.350 | 0.321 | 0.436 |
| retrieve_hop2 | 0.488 | 0.002 | 1.661 |
| summarize_hop2 | 6.313 | 6.044 | 10.095 |
| query_hop3 | 0.372 | 0.341 | 0.608 |
| retrieve_hop3 | 1.207 | 1.369 | 1.682 |
| summarize_hop3 | 8.002 | 6.870 | 13.459 |
| query_hop4 | 0.476 | 0.435 | 0.747 |
| retrieve_hop4 | 1.384 | 1.565 | 1.722 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **21.900** | **20.391** | **31.821** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 73 |
