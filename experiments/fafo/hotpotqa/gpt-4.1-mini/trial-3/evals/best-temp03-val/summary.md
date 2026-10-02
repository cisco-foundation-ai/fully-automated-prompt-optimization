# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.008 |
| summarize_hop1 | 5.833 | 4.966 | 11.527 |
| query_hop2 | 2.466 | 2.296 | 3.722 |
| retrieve_hop2 | 0.537 | 0.003 | 1.506 |
| summarize_hop2 | 4.642 | 4.186 | 7.999 |
| answer | 2.072 | 1.725 | 4.018 |
| **Total** | **15.566** | **14.704** | **24.602** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
