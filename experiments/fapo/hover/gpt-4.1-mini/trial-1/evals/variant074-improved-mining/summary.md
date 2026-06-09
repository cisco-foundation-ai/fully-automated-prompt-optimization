# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- partial_recall: 87.22
- recall: 69.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.010 | 0.023 |
| summarize_hop1 | 5.524 | 4.082 | 12.976 |
| query_hop2 | 0.936 | 0.794 | 1.479 |
| retrieve_hop2 | 1.904 | 1.565 | 4.007 |
| summarize_hop2 | 4.939 | 3.880 | 10.900 |
| query_hop3 | 1.185 | 0.857 | 2.036 |
| retrieve_hop3 | 5.229 | 4.585 | 11.956 |
| retrieve_mining | 0.713 | 0.026 | 3.026 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **20.447** | **18.758** | **36.346** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 93 |
