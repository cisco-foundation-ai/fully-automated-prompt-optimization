# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.00

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- num_missing: 0.30
- partial_recall: 90.00
- recall: 74.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.409 | 2.716 | 7.372 |
| query_hop2 | 1.369 | 0.315 | 0.562 |
| retrieve_hop2 | 0.567 | 0.002 | 1.504 |
| summarize_hop2 | 6.085 | 5.891 | 9.390 |
| query_hop3 | 0.375 | 0.330 | 0.625 |
| retrieve_hop3 | 1.161 | 1.259 | 1.539 |
| summarize_hop3 | 6.672 | 6.161 | 11.752 |
| query_hop4 | 0.487 | 0.419 | 0.932 |
| retrieve_hop4 | 1.316 | 1.312 | 1.557 |
| query_hop5 | 0.434 | 0.370 | 0.738 |
| retrieve_hop5 | 1.312 | 1.298 | 1.574 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.190** | **21.182** | **33.777** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 78 |
