# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 74.82

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.078 | 0.003 | 0.055 |
| summarize_hop1 | 2.342 | 2.192 | 3.854 |
| query_hop2 | 1.017 | 0.966 | 1.472 |
| retrieve_hop2 | 0.524 | 0.003 | 1.629 |
| summarize_hop2 | 2.154 | 2.019 | 3.248 |
| answer | 1.012 | 0.935 | 1.660 |
| **Total** | **7.129** | **6.821** | **10.907** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
