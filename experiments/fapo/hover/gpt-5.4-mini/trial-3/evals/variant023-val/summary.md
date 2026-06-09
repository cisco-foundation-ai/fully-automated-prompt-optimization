# Evaluation Summary

Total cases: 300

## Composite Score
- average: 27.33

## Score Breakdown
- num_found: 1.94
- num_gold: 3.00
- num_missing: 1.06
- partial_recall: 64.78
- recall: 27.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.453 | 0.092 | 1.616 |
| summarize_hop1 | 1.613 | 1.485 | 2.370 |
| query_hop2 | 0.860 | 0.715 | 1.169 |
| retrieve_hop2 | 1.422 | 1.428 | 1.643 |
| summarize_hop2 | 1.875 | 1.812 | 2.602 |
| query_hop3 | 0.864 | 0.711 | 1.074 |
| retrieve_hop3 | 1.390 | 1.503 | 1.635 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.477** | **8.059** | **10.682** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 218 |
