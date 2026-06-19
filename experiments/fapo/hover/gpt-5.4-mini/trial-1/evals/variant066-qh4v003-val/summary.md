# Evaluation Summary

Total cases: 300

## Composite Score
- average: 84.67

## Score Breakdown
- num_found: 2.82
- num_gold: 3.00
- partial_recall: 94.00
- recall: 84.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.009 |
| summarize_hop1 | 3.149 | 2.782 | 5.257 |
| query_hop2 | 0.990 | 0.841 | 1.683 |
| retrieve_hop2 | 0.707 | 0.007 | 1.494 |
| summarize_hop2 | 4.967 | 4.340 | 8.565 |
| query_hop3 | 1.608 | 1.100 | 3.582 |
| retrieve_hop3 | 0.292 | 0.004 | 1.448 |
| query_hop4 | 1.816 | 1.203 | 4.036 |
| retrieve_hop4 | 0.434 | 0.004 | 1.484 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.966** | **12.730** | **22.426** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 46 |
