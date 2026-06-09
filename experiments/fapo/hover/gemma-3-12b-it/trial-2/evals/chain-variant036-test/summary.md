# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.67

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.44
- recall: 79.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.330 | 2.896 | 6.300 |
| query_hop2 | 0.423 | 0.340 | 0.925 |
| retrieve_hop2 | 1.357 | 1.296 | 1.676 |
| summarize_hop2 | 6.508 | 6.050 | 10.311 |
| query_hop3 | 0.450 | 0.352 | 1.179 |
| retrieve_hop3 | 1.118 | 1.284 | 1.657 |
| summarize_hop3 | 8.512 | 7.236 | 13.965 |
| query_hop4 | 0.540 | 0.443 | 1.070 |
| retrieve_hop4 | 1.277 | 1.337 | 1.687 |
| query_hop5 | 0.562 | 0.492 | 0.950 |
| retrieve_hop5 | 2.477 | 2.630 | 3.323 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.558** | **25.198** | **35.777** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 61 |
