# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- partial_recall: 88.22
- recall: 69.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.007 |
| summarize_hop1 | 2.460 | 2.221 | 4.187 |
| query_hop2 | 0.795 | 0.685 | 1.083 |
| retrieve_hop2 | 0.819 | 0.003 | 1.700 |
| summarize_hop2 | 3.489 | 3.091 | 5.841 |
| query_hop3 | 0.725 | 0.635 | 1.087 |
| retrieve_hop3 | 0.707 | 0.003 | 1.681 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.012** | **8.471** | **13.360** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 92 |
