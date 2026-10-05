# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.037 | 0.002 | 0.030 |
| summarize_hop1 | 2.296 | 2.090 | 4.277 |
| query_hop2 | 0.989 | 0.943 | 1.410 |
| retrieve_hop2 | 1.022 | 0.014 | 1.732 |
| summarize_hop2 | 2.022 | 1.942 | 2.808 |
| answer | 0.866 | 0.819 | 1.272 |
| **Total** | **7.232** | **6.775** | **10.759** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
