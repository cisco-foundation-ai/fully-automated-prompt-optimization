# Evaluation Summary

Total cases: 300

## Composite Score
- average: 24.00

## Score Breakdown
- num_found: 1.85
- num_gold: 3.00
- num_missing: 1.15
- partial_recall: 61.78
- recall: 24.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 1.659 | 1.503 | 2.455 |
| query_hop2 | 0.859 | 0.754 | 1.106 |
| retrieve_hop2 | 1.135 | 1.240 | 1.623 |
| summarize_hop2 | 2.340 | 2.183 | 3.078 |
| query_hop3 | 0.961 | 0.752 | 1.202 |
| retrieve_hop3 | 1.143 | 1.464 | 1.617 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.100** | **7.634** | **12.853** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 228 |
