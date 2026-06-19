# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- num_found: 2.66
- num_gold: 3.00
- partial_recall: 88.78
- recall: 71.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.007 |
| summarize_hop1 | 2.267 | 2.050 | 3.593 |
| query_hop2 | 0.745 | 0.660 | 1.090 |
| retrieve_hop2 | 0.836 | 0.010 | 1.662 |
| summarize_hop2 | 1.088 | 0.999 | 1.484 |
| query_hop3 | 0.854 | 0.740 | 1.186 |
| retrieve_hop3 | 1.089 | 1.176 | 1.669 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **6.882** | **6.486** | **10.251** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 86 |
