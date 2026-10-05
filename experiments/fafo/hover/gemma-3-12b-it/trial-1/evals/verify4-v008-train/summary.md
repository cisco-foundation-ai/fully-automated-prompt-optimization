# Evaluation Summary

Total cases: 150

## Composite Score
- average: 87.33

## Score Breakdown
- num_found: 2.87
- num_gold: 3.00
- num_missing: 0.13
- partial_recall: 95.56
- recall: 87.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.647 | 5.264 | 9.480 |
| summarize_hop1 | 3.926 | 3.165 | 9.196 |
| retrieve_hop2 | 5.979 | 6.479 | 8.171 |
| summarize_hop2 | 3.097 | 2.557 | 6.577 |
| retrieve_hop3 | 5.273 | 6.298 | 8.085 |
| summarize_hop3 | 2.483 | 1.880 | 5.841 |
| retrieve_hop4 | 3.506 | 2.788 | 7.604 |
| combine_retrievals | 0.027 | 0.025 | 0.052 |
| **Total** | **29.938** | **29.466** | **42.515** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 19 |
