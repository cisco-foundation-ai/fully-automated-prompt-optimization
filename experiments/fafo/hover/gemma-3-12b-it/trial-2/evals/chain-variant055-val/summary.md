# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.00

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.44
- recall: 77.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.012 |
| summarize_hop1 | 3.568 | 3.038 | 6.714 |
| query_hop2 | 0.398 | 0.322 | 0.863 |
| retrieve_hop2 | 1.328 | 1.438 | 1.659 |
| summarize_hop2 | 6.507 | 6.195 | 10.097 |
| query_hop3 | 0.462 | 0.369 | 0.771 |
| retrieve_hop3 | 1.647 | 1.539 | 3.116 |
| summarize_hop3 | 7.448 | 6.748 | 12.751 |
| query_hop4 | 0.513 | 0.414 | 1.198 |
| retrieve_hop4 | 1.351 | 1.477 | 1.655 |
| query_hop5 | 0.526 | 0.453 | 0.895 |
| retrieve_hop5 | 2.098 | 2.078 | 3.195 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.849** | **25.363** | **34.904** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 69 |
