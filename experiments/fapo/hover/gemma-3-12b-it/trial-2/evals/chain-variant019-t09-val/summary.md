# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- num_missing: 0.29
- partial_recall: 90.22
- recall: 73.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 3.455 | 2.761 | 7.669 |
| query_hop2 | 0.363 | 0.320 | 0.606 |
| retrieve_hop2 | 0.390 | 0.003 | 1.603 |
| summarize_hop2 | 7.114 | 6.074 | 9.950 |
| query_hop3 | 0.409 | 0.341 | 0.753 |
| retrieve_hop3 | 1.206 | 1.329 | 1.654 |
| summarize_hop3 | 10.094 | 7.192 | 13.393 |
| query_hop4 | 0.505 | 0.441 | 0.890 |
| retrieve_hop4 | 1.416 | 1.490 | 1.684 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **24.958** | **20.915** | **34.074** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 81 |
