# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.67

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- partial_recall: 90.89
- recall: 76.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.023 | 0.002 | 0.005 |
| summarize_hop1 | 2.423 | 2.218 | 4.047 |
| query_hop2 | 0.789 | 0.698 | 1.204 |
| retrieve_hop2 | 0.601 | 0.003 | 1.563 |
| summarize_hop2 | 3.648 | 3.186 | 6.793 |
| query_hop3 | 0.745 | 0.666 | 1.265 |
| retrieve_hop3 | 0.226 | 0.002 | 1.351 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.455** | **7.957** | **12.734** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 70 |
