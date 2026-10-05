# Evaluation Summary

Total cases: 300

## Composite Score
- average: 22.67

## Score Breakdown
- num_found: 1.84
- num_gold: 3.00
- partial_recall: 61.22
- recall: 22.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.006 |
| summarize_hop1 | 2.743 | 2.379 | 5.262 |
| query_hop2 | 0.700 | 0.524 | 0.965 |
| retrieve_hop2 | 0.167 | 0.002 | 1.620 |
| summarize_hop2 | 4.227 | 3.695 | 7.697 |
| query_hop3 | 0.723 | 0.556 | 1.199 |
| retrieve_hop3 | 0.689 | 0.002 | 1.652 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.264** | **8.373** | **15.725** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 232 |
