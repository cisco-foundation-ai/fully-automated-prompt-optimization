# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.67

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.56
- recall: 75.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.008 |
| summarize_hop1 | 3.461 | 2.875 | 7.607 |
| query_hop2 | 0.387 | 0.328 | 0.844 |
| retrieve_hop2 | 0.816 | 0.003 | 1.666 |
| summarize_hop2 | 7.674 | 6.163 | 9.740 |
| query_hop3 | 0.444 | 0.349 | 0.914 |
| retrieve_hop3 | 1.255 | 1.361 | 1.685 |
| summarize_hop3 | 8.322 | 6.595 | 12.397 |
| query_hop4 | 0.516 | 0.433 | 1.124 |
| retrieve_hop4 | 1.420 | 1.559 | 1.707 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.301** | **20.846** | **31.220** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 73 |
