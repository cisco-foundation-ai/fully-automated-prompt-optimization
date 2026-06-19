# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.014 |
| summarize_hop1 | 1.587 | 1.448 | 2.719 |
| query_hop2 | 1.132 | 1.030 | 1.879 |
| retrieve_hop2 | 1.002 | 0.127 | 1.686 |
| summarize_hop2 | 1.722 | 1.517 | 2.581 |
| answer | 0.842 | 0.799 | 1.230 |
| **Total** | **6.319** | **5.859** | **8.677** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
