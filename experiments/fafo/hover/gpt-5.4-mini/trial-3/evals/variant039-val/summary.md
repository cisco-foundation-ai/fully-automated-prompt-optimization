# Evaluation Summary

Total cases: 300

## Composite Score
- average: 43.33

## Score Breakdown
- num_found: 2.26
- num_gold: 3.00
- num_missing: 0.74
- partial_recall: 75.44
- recall: 43.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.017 | 0.571 | 1.692 |
| summarize_hop1 | 2.302 | 1.839 | 2.924 |
| query_hop2 | 0.766 | 0.690 | 1.079 |
| retrieve_hop2 | 1.433 | 1.506 | 1.649 |
| summarize_hop2 | 2.434 | 2.143 | 4.017 |
| query_hop3 | 0.760 | 0.716 | 0.978 |
| retrieve_hop3 | 1.407 | 1.478 | 1.651 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.118** | **9.368** | **13.640** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 170 |
