# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.19

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.291 | 0.888 | 1.709 |
| summarize_hop1 | 1.457 | 1.351 | 2.215 |
| query_hop2 | 1.193 | 1.087 | 1.763 |
| retrieve_hop2 | 1.325 | 1.485 | 1.617 |
| summarize_hop2 | 1.740 | 1.617 | 2.664 |
| answer | 0.874 | 0.764 | 1.364 |
| **Total** | **7.880** | **7.381** | **12.472** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
