# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.00

## Score Breakdown
- num_found: 2.53
- num_gold: 3.00
- num_missing: 0.47
- partial_recall: 84.33
- recall: 59.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 5.890 | 5.582 | 11.011 |
| query_hop2 | 0.342 | 0.303 | 0.593 |
| retrieve_hop2 | 0.595 | 0.003 | 1.571 |
| summarize_hop2 | 10.975 | 8.363 | 14.648 |
| query_hop3 | 0.398 | 0.336 | 0.840 |
| retrieve_hop3 | 1.282 | 1.296 | 1.600 |
| summarize_hop3 | 13.543 | 8.979 | 18.542 |
| query_hop4 | 0.409 | 0.340 | 0.842 |
| retrieve_hop4 | 1.237 | 1.307 | 1.603 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **34.675** | **27.901** | **42.273** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 123 |
