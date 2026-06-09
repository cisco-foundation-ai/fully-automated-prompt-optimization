# Evaluation Summary

Total cases: 150

## Composite Score
- average: 87.33

## Score Breakdown
- num_found: 2.87
- num_gold: 3.00
- num_missing: 0.13
- partial_recall: 95.78
- recall: 87.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.928 | 5.473 | 10.382 |
| summarize_hop1 | 1.962 | 1.591 | 3.866 |
| retrieve_hop2 | 5.456 | 6.138 | 8.182 |
| summarize_hop2 | 1.667 | 1.369 | 3.729 |
| retrieve_hop3 | 4.279 | 4.451 | 7.983 |
| combine_retrievals | 0.017 | 0.016 | 0.034 |
| **Total** | **19.308** | **19.355** | **27.079** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 19 |
