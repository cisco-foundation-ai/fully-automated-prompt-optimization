# Evaluation Summary

Total cases: 150

## Composite Score
- average: 78.67

## Score Breakdown
- exact_match: 78.67
- f1: 82.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.008 |
| summarize_hop1 | 4.798 | 4.304 | 8.137 |
| query_hop2 | 2.577 | 2.405 | 4.370 |
| retrieve_hop2 | 1.296 | 1.340 | 1.654 |
| summarize_hop2 | 4.032 | 3.801 | 7.186 |
| answer | 1.948 | 1.629 | 4.409 |
| **Total** | **14.666** | **13.737** | **23.905** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 32 |
