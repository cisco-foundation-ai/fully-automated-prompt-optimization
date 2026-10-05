# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 80.20

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.003 | 0.024 |
| summarize_hop1 | 3.046 | 2.519 | 5.669 |
| query_hop2 | 1.661 | 1.527 | 2.628 |
| retrieve_hop2 | 0.475 | 0.002 | 1.328 |
| summarize_hop2 | 3.212 | 2.827 | 5.679 |
| answer | 1.617 | 1.492 | 2.409 |
| **Total** | **10.040** | **9.330** | **15.312** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
