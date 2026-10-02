# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.44
- recall: 72.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.439 | 2.197 | 3.910 |
| query_hop2 | 0.891 | 0.744 | 1.171 |
| retrieve_hop2 | 1.586 | 1.474 | 1.630 |
| summarize_hop2 | 2.095 | 1.934 | 3.164 |
| query_hop3 | 0.866 | 0.606 | 0.899 |
| retrieve_hop3 | 0.156 | 0.002 | 1.453 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.036** | **7.154** | **13.688** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 83 |
