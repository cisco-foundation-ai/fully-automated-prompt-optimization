# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.00

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.22
- recall: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.799 | 3.000 | 7.874 |
| query_hop2 | 0.420 | 0.333 | 0.788 |
| retrieve_hop2 | 0.781 | 0.007 | 1.641 |
| summarize_hop2 | 6.792 | 6.348 | 10.927 |
| query_hop3 | 0.417 | 0.358 | 0.651 |
| retrieve_hop3 | 1.034 | 1.295 | 1.648 |
| summarize_hop3 | 8.335 | 7.361 | 13.854 |
| query_hop4 | 0.625 | 0.466 | 1.368 |
| retrieve_hop4 | 2.671 | 2.697 | 3.269 |
| query_hop5 | 0.701 | 0.493 | 1.910 |
| retrieve_hop5 | 2.471 | 2.655 | 3.288 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.050** | **26.847** | **36.946** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 72 |
