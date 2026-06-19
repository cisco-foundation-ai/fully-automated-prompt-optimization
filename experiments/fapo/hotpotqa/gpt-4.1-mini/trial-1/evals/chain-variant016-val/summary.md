# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.002 | 0.007 |
| summarize_hop1 | 2.891 | 2.720 | 4.758 |
| query_hop2 | 1.658 | 1.532 | 2.745 |
| retrieve_hop2 | 0.644 | 0.006 | 1.532 |
| summarize_hop2 | 2.763 | 2.515 | 4.163 |
| answer | 1.557 | 1.420 | 2.550 |
| **Total** | **9.537** | **9.037** | **13.364** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
