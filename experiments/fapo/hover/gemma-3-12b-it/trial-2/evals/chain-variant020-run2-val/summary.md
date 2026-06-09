# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.67

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- num_missing: 0.31
- partial_recall: 89.78
- recall: 71.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 5.817 | 5.649 | 9.140 |
| query_hop2 | 0.342 | 0.309 | 0.449 |
| retrieve_hop2 | 0.758 | 0.003 | 1.642 |
| summarize_hop2 | 7.433 | 6.464 | 11.579 |
| query_hop3 | 0.379 | 0.344 | 0.504 |
| retrieve_hop3 | 1.226 | 1.547 | 1.682 |
| summarize_hop3 | 9.367 | 8.536 | 15.561 |
| query_hop4 | 0.525 | 0.449 | 0.968 |
| retrieve_hop4 | 1.525 | 1.599 | 1.717 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **27.376** | **25.303** | **37.987** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 85 |
