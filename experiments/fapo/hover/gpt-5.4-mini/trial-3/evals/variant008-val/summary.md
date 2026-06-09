# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.00

## Score Breakdown
- num_found: 1.86
- num_gold: 3.00
- num_missing: 1.14
- partial_recall: 62.00
- recall: 23.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.013 | 0.002 | 0.005 |
| summarize_hop1 | 1.754 | 1.522 | 2.451 |
| query_hop2 | 0.869 | 0.736 | 1.211 |
| retrieve_hop2 | 1.169 | 1.273 | 1.606 |
| summarize_hop2 | 1.946 | 1.773 | 2.804 |
| query_hop3 | 0.885 | 0.752 | 1.181 |
| retrieve_hop3 | 1.158 | 1.289 | 1.604 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.795** | **7.409** | **12.007** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 231 |
