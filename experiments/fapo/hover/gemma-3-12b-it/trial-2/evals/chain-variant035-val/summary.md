# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.67

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.33
- recall: 75.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.321 | 2.955 | 6.054 |
| query_hop2 | 0.389 | 0.319 | 0.766 |
| retrieve_hop2 | 0.970 | 1.074 | 1.589 |
| summarize_hop2 | 7.094 | 5.993 | 10.475 |
| query_hop3 | 0.408 | 0.336 | 0.799 |
| retrieve_hop3 | 1.016 | 1.091 | 1.599 |
| summarize_hop3 | 8.434 | 7.550 | 13.860 |
| query_hop4 | 0.504 | 0.434 | 0.922 |
| retrieve_hop4 | 1.255 | 1.328 | 1.637 |
| query_hop5 | 0.556 | 0.490 | 1.019 |
| retrieve_hop5 | 2.214 | 2.171 | 3.228 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.163** | **24.145** | **33.986** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 73 |
