# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.67

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.22
- recall: 79.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.268 | 2.885 | 6.877 |
| query_hop2 | 0.442 | 0.338 | 0.979 |
| retrieve_hop2 | 1.200 | 1.286 | 1.605 |
| summarize_hop2 | 7.574 | 6.062 | 9.785 |
| query_hop3 | 0.396 | 0.334 | 0.626 |
| retrieve_hop3 | 1.073 | 1.288 | 1.588 |
| summarize_hop3 | 9.548 | 7.119 | 13.906 |
| query_hop4 | 0.520 | 0.418 | 1.064 |
| retrieve_hop4 | 1.314 | 1.333 | 1.614 |
| query_hop5 | 0.569 | 0.482 | 1.190 |
| retrieve_hop5 | 2.354 | 2.564 | 3.163 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.263** | **24.067** | **34.494** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 61 |
