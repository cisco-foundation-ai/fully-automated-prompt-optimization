# Evaluation Summary

Total cases: 150

## Composite Score
- average: 64.00

## Score Breakdown
- num_found: 2.62
- num_gold: 3.00
- num_missing: 0.38
- partial_recall: 87.33
- recall: 64.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_claim | 0.013 | 0.006 | 0.052 |
| extract_entities | 0.649 | 0.544 | 1.121 |
| retrieve_entities | 0.481 | 0.006 | 0.034 |
| combine | 0.002 | 0.002 | 0.003 |
| **Total** | **1.145** | **0.568** | **1.162** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_entities | 54 |
