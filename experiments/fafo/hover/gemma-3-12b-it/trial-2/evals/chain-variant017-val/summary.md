# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.00

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- num_missing: 0.37
- partial_recall: 87.78
- recall: 66.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.413 | 2.951 | 6.957 |
| query_hop2 | 0.358 | 0.324 | 0.593 |
| retrieve_hop2 | 0.698 | 0.003 | 1.619 |
| summarize_hop2 | 10.856 | 7.988 | 13.295 |
| query_hop3 | 0.409 | 0.340 | 0.836 |
| retrieve_hop3 | 0.652 | 0.007 | 1.626 |
| summarize_hop3 | 12.332 | 10.383 | 18.209 |
| query_hop4 | 0.397 | 0.355 | 0.621 |
| retrieve_hop4 | 1.025 | 1.534 | 1.646 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **30.143** | **25.106** | **39.487** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 102 |
