# Evaluation Summary

Total cases: 300

## Composite Score
- average: 52.67

## Score Breakdown
- num_found: 2.46
- num_gold: 3.00
- num_missing: 0.54
- partial_recall: 82.11
- recall: 52.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.042 | 0.588 | 1.743 |
| summarize_hop1 | 2.823 | 2.492 | 4.825 |
| query_hop2 | 0.793 | 0.713 | 1.080 |
| retrieve_hop2 | 1.455 | 1.532 | 1.668 |
| summarize_hop2 | 3.859 | 3.292 | 7.460 |
| query_hop3 | 0.868 | 0.701 | 1.091 |
| retrieve_hop3 | 1.439 | 1.538 | 1.656 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **12.279** | **11.751** | **17.974** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 142 |
