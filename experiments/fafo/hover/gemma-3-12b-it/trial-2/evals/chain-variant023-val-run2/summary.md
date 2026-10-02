# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.67

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.67
- recall: 75.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 3.305 | 2.800 | 6.837 |
| query_hop2 | 0.396 | 0.327 | 0.582 |
| retrieve_hop2 | 0.327 | 0.002 | 1.489 |
| summarize_hop2 | 7.566 | 6.222 | 10.127 |
| query_hop3 | 0.407 | 0.346 | 0.602 |
| retrieve_hop3 | 1.046 | 1.240 | 1.544 |
| summarize_hop3 | 7.268 | 6.747 | 12.762 |
| query_hop4 | 0.516 | 0.443 | 0.969 |
| retrieve_hop4 | 1.307 | 1.373 | 1.580 |
| query_hop5 | 0.448 | 0.388 | 0.799 |
| retrieve_hop5 | 1.344 | 1.446 | 1.587 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.933** | **22.118** | **32.171** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 73 |
