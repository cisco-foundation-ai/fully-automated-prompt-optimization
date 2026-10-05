# Evaluation Summary

Total cases: 300

## Composite Score
- average: 17.00

## Score Breakdown
- num_found: 1.73
- num_gold: 3.00
- num_missing: 1.27
- partial_recall: 57.78
- recall: 17.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.083 | 1.109 | 1.652 |
| summarize_hop1 | 2.645 | 0.750 | 4.721 |
| query_hop2 | 4.011 | 1.280 | 8.565 |
| retrieve_hop2 | 0.790 | 1.079 | 1.626 |
| summarize_hop2 | 3.062 | 0.813 | 5.867 |
| query_hop3 | 6.135 | 2.772 | 8.339 |
| retrieve_hop3 | 0.524 | 0.108 | 1.626 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **18.250** | **8.924** | **26.290** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 249 |
