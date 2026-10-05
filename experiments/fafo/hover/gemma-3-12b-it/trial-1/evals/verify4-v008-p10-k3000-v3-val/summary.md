# Evaluation Summary

Total cases: 300

## Composite Score
- average: 87.33

## Score Breakdown
- num_found: 2.87
- num_gold: 3.00
- num_missing: 0.13
- partial_recall: 95.67
- recall: 87.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.600 | 4.268 | 8.126 |
| summarize_hop1 | 1.631 | 1.315 | 3.674 |
| retrieve_hop2 | 7.780 | 8.207 | 13.188 |
| summarize_hop2 | 1.352 | 1.200 | 2.642 |
| retrieve_hop3 | 3.323 | 2.298 | 9.631 |
| summarize_hop3 | 1.284 | 1.117 | 2.354 |
| retrieve_hop4 | 1.625 | 1.255 | 5.220 |
| combine_retrievals | 0.052 | 0.046 | 0.114 |
| **Total** | **21.648** | **19.991** | **36.224** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 38 |
