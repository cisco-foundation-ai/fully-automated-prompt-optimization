# Evaluation Summary

Total cases: 300

## Composite Score
- average: 81.00

## Score Breakdown
- num_found: 2.79
- num_gold: 3.00
- num_missing: 0.21
- partial_recall: 92.89
- recall: 81.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.011 |
| summarize_hop1 | 3.175 | 2.687 | 6.154 |
| query_hop2 | 0.401 | 0.329 | 0.792 |
| retrieve_hop2 | 1.046 | 1.280 | 1.619 |
| summarize_hop2 | 6.105 | 5.769 | 9.595 |
| query_hop3 | 1.511 | 0.377 | 1.160 |
| retrieve_hop3 | 2.171 | 2.549 | 3.161 |
| summarize_hop3 | 7.068 | 6.189 | 11.397 |
| query_hop4 | 0.505 | 0.415 | 1.210 |
| retrieve_hop4 | 1.325 | 1.337 | 1.635 |
| query_hop5 | 0.628 | 0.460 | 1.497 |
| retrieve_hop5 | 2.245 | 2.559 | 3.197 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.184** | **24.111** | **33.949** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 57 |
