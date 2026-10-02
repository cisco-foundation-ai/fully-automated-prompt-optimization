# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 76.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.098 | 0.002 | 0.077 |
| summarize_hop1 | 2.553 | 2.308 | 4.450 |
| query_hop2 | 1.341 | 1.296 | 1.886 |
| retrieve_hop2 | 0.514 | 0.003 | 1.667 |
| summarize_hop2 | 2.336 | 2.151 | 3.686 |
| answer | 1.031 | 0.952 | 1.414 |
| **Total** | **7.872** | **7.291** | **11.648** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
