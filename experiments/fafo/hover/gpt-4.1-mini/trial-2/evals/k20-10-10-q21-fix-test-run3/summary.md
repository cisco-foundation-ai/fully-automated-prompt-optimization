# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.00

## Score Breakdown
- num_found: 2.57
- num_gold: 3.00
- partial_recall: 85.67
- recall: 65.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.007 | 0.002 | 0.003 |
| summarize_hop1 | 4.076 | 3.510 | 7.605 |
| query_hop2 | 0.933 | 0.574 | 1.162 |
| retrieve_hop2 | 0.516 | 0.003 | 1.526 |
| summarize_hop2 | 4.146 | 3.543 | 7.312 |
| query_hop3 | 0.789 | 0.590 | 1.410 |
| retrieve_hop3 | 0.636 | 0.007 | 1.539 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.103** | **9.840** | **21.427** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 105 |
