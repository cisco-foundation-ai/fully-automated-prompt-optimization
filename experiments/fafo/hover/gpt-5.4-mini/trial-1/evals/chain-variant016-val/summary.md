# Evaluation Summary

Total cases: 300

## Composite Score
- average: 53.67

## Score Breakdown
- num_found: 2.48
- num_gold: 3.00
- partial_recall: 82.67
- recall: 53.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.006 |
| summarize_hop1 | 1.063 | 0.842 | 1.341 |
| query_hop2 | 0.803 | 0.712 | 1.039 |
| retrieve_hop2 | 1.393 | 1.343 | 1.647 |
| summarize_hop2 | 1.708 | 1.506 | 2.678 |
| query_hop3 | 0.705 | 0.596 | 0.871 |
| retrieve_hop3 | 0.351 | 0.002 | 1.576 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **6.026** | **5.264** | **10.099** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 139 |
