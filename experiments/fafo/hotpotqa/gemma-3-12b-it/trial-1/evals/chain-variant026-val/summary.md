# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 71.12

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.013 |
| summarize_hop1 | 2.355 | 2.199 | 3.864 |
| query_hop2 | 1.048 | 0.990 | 1.466 |
| retrieve_hop2 | 0.570 | 0.003 | 1.632 |
| summarize_hop2 | 2.644 | 2.511 | 4.044 |
| answer | 0.885 | 0.817 | 1.212 |
| **Total** | **7.541** | **7.342** | **11.170** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 112 |
