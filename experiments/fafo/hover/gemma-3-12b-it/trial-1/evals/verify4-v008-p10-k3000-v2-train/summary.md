# Evaluation Summary

Total cases: 150

## Composite Score
- average: 90.00

## Score Breakdown
- num_found: 2.90
- num_gold: 3.00
- num_missing: 0.10
- partial_recall: 96.67
- recall: 90.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.859 | 5.376 | 11.928 |
| summarize_hop1 | 1.642 | 1.464 | 3.493 |
| retrieve_hop2 | 7.712 | 7.080 | 14.195 |
| summarize_hop2 | 1.438 | 1.281 | 2.831 |
| retrieve_hop3 | 3.538 | 3.308 | 7.955 |
| summarize_hop3 | 1.343 | 1.139 | 2.764 |
| retrieve_hop4 | 1.901 | 1.541 | 4.955 |
| combine_retrievals | 0.041 | 0.036 | 0.088 |
| **Total** | **23.474** | **23.348** | **36.661** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 15 |
