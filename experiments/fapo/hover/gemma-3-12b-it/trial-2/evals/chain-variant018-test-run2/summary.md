# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- num_missing: 0.33
- partial_recall: 89.00
- recall: 71.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 4.024 | 2.675 | 7.694 |
| query_hop2 | 0.379 | 0.332 | 0.609 |
| retrieve_hop2 | 1.019 | 1.292 | 1.672 |
| summarize_hop2 | 9.219 | 7.357 | 12.865 |
| query_hop3 | 0.381 | 0.342 | 0.673 |
| retrieve_hop3 | 1.028 | 1.293 | 1.704 |
| summarize_hop3 | 7.480 | 7.234 | 13.623 |
| query_hop4 | 0.490 | 0.438 | 0.704 |
| retrieve_hop4 | 1.425 | 1.589 | 1.709 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.447** | **22.195** | **35.715** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 87 |
