# Evaluation Summary

Total cases: 300

## Composite Score
- average: 17.33

## Score Breakdown
- num_found: 1.75
- num_gold: 3.00
- num_missing: 1.25
- partial_recall: 58.33
- recall: 17.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 6.778 | 6.559 | 10.200 |
| query_hop2 | 0.909 | 0.744 | 1.109 |
| retrieve_hop2 | 1.206 | 1.230 | 1.619 |
| summarize_hop2 | 6.404 | 5.758 | 9.249 |
| query_hop3 | 0.938 | 0.762 | 1.321 |
| retrieve_hop3 | 1.130 | 1.083 | 1.621 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **17.369** | **16.521** | **27.623** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 248 |
