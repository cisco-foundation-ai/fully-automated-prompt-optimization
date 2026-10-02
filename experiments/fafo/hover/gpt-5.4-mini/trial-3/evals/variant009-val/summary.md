# Evaluation Summary

Total cases: 300

## Composite Score
- average: 20.33

## Score Breakdown
- num_found: 1.77
- num_gold: 3.00
- num_missing: 1.23
- partial_recall: 59.11
- recall: 20.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.004 |
| summarize_hop1 | 2.087 | 1.993 | 2.882 |
| query_hop2 | 0.902 | 0.751 | 1.224 |
| retrieve_hop2 | 1.548 | 1.454 | 1.641 |
| summarize_hop2 | 2.102 | 1.985 | 2.985 |
| query_hop3 | 0.976 | 0.749 | 1.189 |
| retrieve_hop3 | 1.227 | 1.365 | 1.637 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.845** | **8.359** | **13.671** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 239 |
