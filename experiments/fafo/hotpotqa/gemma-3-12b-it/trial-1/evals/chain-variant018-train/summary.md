# Evaluation Summary

Total cases: 150

## Composite Score
- average: 64.67

## Score Breakdown
- exact_match: 64.67
- f1: 70.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.054 | 0.002 | 0.036 |
| summarize_hop1 | 1.990 | 1.825 | 3.564 |
| query_hop2 | 1.301 | 1.285 | 1.749 |
| retrieve_hop2 | 0.703 | 0.007 | 1.635 |
| summarize_hop2 | 2.202 | 2.073 | 3.686 |
| answer | 1.067 | 1.034 | 1.556 |
| **Total** | **7.318** | **6.868** | **10.212** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 53 |
