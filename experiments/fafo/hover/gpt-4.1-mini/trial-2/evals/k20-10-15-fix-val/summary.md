# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.67

## Score Breakdown
- num_found: 2.59
- num_gold: 3.00
- partial_recall: 86.22
- recall: 64.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 6.640 | 3.942 | 18.092 |
| query_hop2 | 1.528 | 0.578 | 4.210 |
| retrieve_hop2 | 0.209 | 0.002 | 1.483 |
| summarize_hop2 | 6.523 | 4.224 | 19.778 |
| query_hop3 | 1.476 | 0.631 | 5.459 |
| retrieve_hop3 | 1.134 | 1.448 | 1.571 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **17.514** | **12.018** | **48.001** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 106 |
