# Evaluation Summary

Total cases: 300

## Composite Score
- average: 36.33

## Score Breakdown
- num_found: 2.15
- num_gold: 3.00
- num_missing: 0.85
- partial_recall: 71.67
- recall: 36.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.017 | 0.550 | 1.704 |
| summarize_hop1 | 1.859 | 1.690 | 2.682 |
| query_hop2 | 0.930 | 0.708 | 1.135 |
| retrieve_hop2 | 1.431 | 1.502 | 1.640 |
| summarize_hop2 | 2.151 | 1.974 | 3.506 |
| query_hop3 | 0.824 | 0.700 | 1.199 |
| retrieve_hop3 | 1.424 | 1.474 | 1.626 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.636** | **9.040** | **12.427** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 191 |
