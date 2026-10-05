# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.33

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.44
- recall: 76.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 3.228 | 2.923 | 6.184 |
| query_hop2 | 0.435 | 0.315 | 1.014 |
| retrieve_hop2 | 0.848 | 1.211 | 1.648 |
| summarize_hop2 | 6.467 | 6.146 | 10.875 |
| query_hop3 | 0.491 | 0.370 | 1.409 |
| retrieve_hop3 | 2.541 | 2.585 | 3.265 |
| summarize_hop3 | 8.130 | 7.142 | 12.751 |
| query_hop4 | 0.572 | 0.412 | 1.107 |
| retrieve_hop4 | 1.370 | 1.371 | 1.682 |
| query_hop5 | 0.563 | 0.467 | 0.977 |
| retrieve_hop5 | 2.663 | 2.655 | 3.289 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **27.312** | **26.237** | **36.285** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 71 |
