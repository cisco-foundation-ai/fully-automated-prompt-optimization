# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 73.73

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.107 | 0.002 | 0.126 |
| summarize_hop1 | 1.208 | 1.050 | 1.731 |
| query_hop2 | 1.103 | 1.024 | 1.565 |
| retrieve_hop2 | 0.787 | 0.003 | 1.691 |
| summarize_hop2 | 1.350 | 1.236 | 2.002 |
| answer | 0.805 | 0.746 | 1.383 |
| **Total** | **5.359** | **4.746** | **8.925** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
