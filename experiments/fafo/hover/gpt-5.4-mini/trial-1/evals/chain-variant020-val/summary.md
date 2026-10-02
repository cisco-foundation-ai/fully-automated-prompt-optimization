# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- num_found: 2.68
- num_gold: 3.00
- partial_recall: 89.22
- recall: 71.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.020 | 0.002 | 0.010 |
| summarize_hop1 | 2.445 | 2.121 | 3.943 |
| query_hop2 | 0.820 | 0.718 | 1.048 |
| retrieve_hop2 | 0.881 | 1.065 | 1.606 |
| summarize_hop2 | 2.129 | 1.819 | 3.022 |
| query_hop3 | 0.714 | 0.603 | 0.899 |
| retrieve_hop3 | 0.120 | 0.002 | 1.087 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.128** | **6.441** | **13.475** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 86 |
