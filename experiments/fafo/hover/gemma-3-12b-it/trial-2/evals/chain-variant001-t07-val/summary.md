# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- num_missing: 0.38
- partial_recall: 87.22
- recall: 65.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.009 |
| summarize_hop1 | 3.491 | 2.882 | 7.539 |
| query_hop2 | 0.382 | 0.329 | 0.617 |
| retrieve_hop2 | 0.534 | 0.005 | 1.645 |
| summarize_hop2 | 13.488 | 8.002 | 17.533 |
| query_hop3 | 0.416 | 0.346 | 0.881 |
| retrieve_hop3 | 0.731 | 0.009 | 1.648 |
| summarize_hop3 | 15.867 | 10.750 | 20.738 |
| query_hop4 | 0.416 | 0.358 | 0.689 |
| retrieve_hop4 | 0.840 | 1.088 | 1.656 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **36.167** | **25.389** | **61.191** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 104 |
