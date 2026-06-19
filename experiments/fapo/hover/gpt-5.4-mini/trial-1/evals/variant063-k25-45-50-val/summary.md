# Evaluation Summary

Total cases: 300

## Composite Score
- average: 80.33

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- partial_recall: 92.11
- recall: 80.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.967 | 0.510 | 1.598 |
| summarize_hop1 | 2.633 | 2.317 | 4.682 |
| query_hop2 | 0.910 | 0.812 | 1.543 |
| retrieve_hop2 | 1.321 | 1.290 | 1.559 |
| summarize_hop2 | 3.969 | 3.441 | 6.953 |
| query_hop3 | 1.189 | 0.877 | 1.852 |
| retrieve_hop3 | 0.310 | 0.002 | 1.436 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.299** | **10.508** | **17.617** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 59 |
