# Evaluation Summary

Total cases: 300

## Composite Score
- average: 19.00

## Score Breakdown
- num_found: 1.78
- num_gold: 3.00
- partial_recall: 59.33
- recall: 19.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.004 |
| summarize_hop1 | 2.575 | 2.301 | 4.525 |
| query_hop2 | 0.719 | 0.537 | 1.136 |
| retrieve_hop2 | 0.227 | 0.002 | 1.550 |
| summarize_hop2 | 2.793 | 2.522 | 4.424 |
| query_hop3 | 0.696 | 0.552 | 0.999 |
| retrieve_hop3 | 0.511 | 0.002 | 1.603 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.536** | **6.916** | **11.923** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 243 |
