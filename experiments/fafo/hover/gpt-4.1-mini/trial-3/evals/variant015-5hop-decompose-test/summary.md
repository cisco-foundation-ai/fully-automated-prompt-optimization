# Evaluation Summary

Total cases: 300

## Composite Score
- average: 98.00

## Score Breakdown
- num_found: 2.98
- num_gold: 3.00
- partial_recall: 99.22
- recall: 98.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.113 | 1.198 | 1.687 |
| summarize_hop1 | 31.645 | 26.988 | 60.195 |
| query_hop2 | 1.187 | 1.067 | 1.733 |
| retrieve_hop2 | 10.554 | 10.809 | 12.457 |
| summarize_hop2 | 31.321 | 26.646 | 56.005 |
| query_hop3 | 1.386 | 1.227 | 1.808 |
| retrieve_hop3 | 8.917 | 8.977 | 12.182 |
| summarize_hop3 | 31.155 | 27.032 | 54.773 |
| query_hop4 | 1.854 | 1.452 | 3.347 |
| retrieve_hop4 | 10.509 | 10.397 | 15.009 |
| summarize_hop4 | 39.589 | 34.913 | 67.791 |
| query_hop5 | 2.564 | 2.136 | 4.490 |
| retrieve_hop5 | 18.541 | 18.498 | 24.469 |
| combine_retrievals | 0.011 | 0.010 | 0.022 |
| **Total** | **190.345** | **184.067** | **252.386** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 6 |
