# Evaluation Summary

Total cases: 300

## Composite Score
- average: 33.67

## Score Breakdown
- num_found: 2.06
- num_gold: 3.00
- num_missing: 0.94
- partial_recall: 68.78
- recall: 33.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.037 | 0.564 | 1.714 |
| summarize_hop1 | 1.934 | 1.646 | 2.940 |
| query_hop2 | 0.795 | 0.667 | 0.990 |
| retrieve_hop2 | 1.431 | 1.503 | 1.652 |
| summarize_hop2 | 2.189 | 1.970 | 3.487 |
| query_hop3 | 0.931 | 0.668 | 1.355 |
| retrieve_hop3 | 1.460 | 1.522 | 1.668 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.777** | **8.991** | **13.401** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 199 |
