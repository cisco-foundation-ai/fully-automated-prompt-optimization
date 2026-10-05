# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.00

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 91.89
- recall: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 3.135 | 2.722 | 5.920 |
| query_hop2 | 0.378 | 0.326 | 0.711 |
| retrieve_hop2 | 0.743 | 0.006 | 1.636 |
| summarize_hop2 | 6.370 | 5.754 | 10.222 |
| query_hop3 | 0.483 | 0.378 | 0.960 |
| retrieve_hop3 | 1.959 | 1.601 | 3.231 |
| summarize_hop3 | 7.222 | 6.242 | 11.890 |
| query_hop4 | 0.500 | 0.414 | 0.928 |
| retrieve_hop4 | 1.429 | 1.546 | 1.668 |
| query_hop5 | 0.547 | 0.455 | 1.077 |
| retrieve_hop5 | 2.215 | 2.126 | 3.217 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **24.984** | **23.812** | **34.096** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 63 |
