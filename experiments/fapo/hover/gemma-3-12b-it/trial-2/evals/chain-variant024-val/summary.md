# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- num_missing: 0.28
- partial_recall: 90.67
- recall: 75.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.011 |
| summarize_hop1 | 3.340 | 2.659 | 7.195 |
| query_hop2 | 0.370 | 0.312 | 0.767 |
| retrieve_hop2 | 0.390 | 0.002 | 1.514 |
| summarize_hop2 | 6.680 | 5.920 | 9.563 |
| query_hop3 | 0.361 | 0.324 | 0.629 |
| retrieve_hop3 | 1.017 | 1.326 | 1.539 |
| summarize_hop3 | 8.768 | 6.194 | 13.309 |
| query_hop4 | 0.477 | 0.419 | 0.771 |
| retrieve_hop4 | 1.389 | 1.466 | 1.591 |
| query_hop5 | 0.433 | 0.368 | 0.825 |
| retrieve_hop5 | 1.392 | 1.467 | 1.573 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.620** | **21.205** | **31.440** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 74 |
