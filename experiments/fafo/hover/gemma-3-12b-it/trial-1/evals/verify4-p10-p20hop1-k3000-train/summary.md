# Evaluation Summary

Total cases: 150

## Composite Score
- average: 89.33

## Score Breakdown
- num_found: 2.89
- num_gold: 3.00
- num_missing: 0.11
- partial_recall: 96.44
- recall: 89.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.813 | 5.379 | 9.817 |
| summarize_hop1 | 1.944 | 1.587 | 4.199 |
| retrieve_hop2 | 8.696 | 9.238 | 14.435 |
| summarize_hop2 | 1.568 | 1.246 | 3.839 |
| retrieve_hop3 | 5.138 | 3.992 | 12.284 |
| summarize_hop3 | 1.437 | 1.167 | 3.105 |
| retrieve_hop4 | 2.055 | 1.665 | 5.604 |
| combine_retrievals | 0.054 | 0.046 | 0.121 |
| **Total** | **26.705** | **27.627** | **42.334** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 16 |
