# Evaluation Summary

Total cases: 300

## Composite Score
- average: 51.33

## Score Breakdown
- num_found: 2.42
- num_gold: 3.00
- partial_recall: 80.78
- recall: 51.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.012 | 0.002 | 0.010 |
| summarize_hop1 | 1.817 | 1.703 | 2.485 |
| query_hop2 | 0.841 | 0.663 | 1.055 |
| retrieve_hop2 | 1.108 | 1.484 | 1.663 |
| summarize_hop2 | 1.754 | 1.640 | 2.565 |
| query_hop3 | 0.773 | 0.627 | 1.182 |
| retrieve_hop3 | 0.702 | 0.002 | 1.660 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.006** | **6.575** | **9.409** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 146 |
