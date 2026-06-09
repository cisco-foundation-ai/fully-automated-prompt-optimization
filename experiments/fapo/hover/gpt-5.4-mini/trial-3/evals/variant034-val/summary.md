# Evaluation Summary

Total cases: 300

## Composite Score
- average: 37.00

## Score Breakdown
- num_found: 2.16
- num_gold: 3.00
- num_missing: 0.84
- partial_recall: 72.11
- recall: 37.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 1.749 | 1.643 | 2.683 |
| query_hop2 | 0.830 | 0.669 | 1.254 |
| retrieve_hop2 | 1.464 | 1.554 | 1.677 |
| summarize_hop2 | 2.256 | 2.011 | 3.401 |
| query_hop3 | 0.741 | 0.664 | 1.082 |
| retrieve_hop3 | 1.327 | 1.544 | 1.671 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.371** | **8.002** | **10.964** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 189 |
