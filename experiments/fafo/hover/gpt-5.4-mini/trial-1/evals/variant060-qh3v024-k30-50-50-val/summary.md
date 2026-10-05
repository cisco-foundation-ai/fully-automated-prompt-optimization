# Evaluation Summary

Total cases: 300

## Composite Score
- average: 80.33

## Score Breakdown
- num_found: 2.78
- num_gold: 3.00
- partial_recall: 92.78
- recall: 80.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.009 |
| summarize_hop1 | 2.657 | 2.325 | 4.554 |
| query_hop2 | 0.996 | 0.772 | 1.728 |
| retrieve_hop2 | 0.828 | 1.040 | 1.494 |
| summarize_hop2 | 3.840 | 3.437 | 6.495 |
| query_hop3 | 1.097 | 0.903 | 2.020 |
| retrieve_hop3 | 0.355 | 0.002 | 1.305 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.782** | **9.066** | **14.845** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 59 |
